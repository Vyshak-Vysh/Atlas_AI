"""The agent's read-only tool registry (ATLASAI_MASTER_SPEC.md §4).

Every tool here is:

*   **Project-scoped.** Each implementation receives the run's tenant and
    project from `ToolExecutionContext` and passes them to a scoped
    repository or to `hybrid_candidates`. No tool takes a tenant or project
    argument from the model, so a model cannot ask for another tenant's
    data even if its prompt is poisoned into trying.
*   **Read-only.** There is no write tool. External writes go through the
    PROPOSE_ACTION / WAIT_APPROVAL branch, which requires a human.
*   **Budgeted.** `ToolExecutionContext.execute` counts every invocation and
    refuses one past `RunLimits.max_calls_per_tool`, so a model looping on a
    single tool terminates deterministically.
*   **Allowlisted at dispatch.** A name outside `_REGISTRY` raises
    `ToolInvocationError` and is never dispatched - the allowlist is
    enforced here, not merely described in the system prompt.

`search_evidence` additionally accumulates every candidate it returns into
`ToolExecutionContext.collected`, which is what RERANK and ANALYZE consume.
The model's job is to decide *what* to look for; the evidence packet the
finding is built from is still assembled from authoritative database rows,
never from anything the model wrote.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_db.repositories.evidence import SourceRecordRepository
from atlasai_db.repositories.requirements import RequirementRepository
from atlasai_domain.agent.limits import RunLimits
from atlasai_domain.agent.tools import (
    ToolBudgetExceededError,
    ToolCall,
    ToolInvocationError,
    ToolResult,
    ToolSpec,
)
from atlasai_domain.contracts.evidence import EvidenceCandidate
from atlasai_retrieval import EmbedderClient, hybrid_candidates

_MAX_SEARCH_LIMIT = 25
_MAX_CONTENT_CHARS = 1200


TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="search_evidence",
        description=(
            "Search this project's indexed evidence (contracts, statements of work, emails, "
            "meeting notes, tickets) using hybrid keyword + semantic retrieval. Returns matching "
            "excerpts, each with an evidence_chunk_id you must use verbatim when citing it. "
            "Call this multiple times with different phrasings to cover a question that has "
            "several parts, or to check whether a later document supersedes an earlier one."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language search query. Be specific; use the vocabulary "
                    "you expect the source document to use.",
                },
                "limit": {
                    "type": "integer",
                    "description": f"Maximum excerpts to return (1-{_MAX_SEARCH_LIMIT}). Defaults to 10.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    ),
    ToolSpec(
        name="list_project_sources",
        description=(
            "List the source documents available for this project, with their titles and types. "
            "Use this to find out what evidence exists at all before concluding that something is "
            "unsupported - absence from search results is not the same as absence from the project."
        ),
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    ToolSpec(
        name="list_requirements",
        description=(
            "List this project's tracked requirements with their key, title, scope status and "
            "delivery status. Use this to ground a scope or delivery question in what the project "
            "formally tracks, rather than inferring it from prose alone."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Optional scope-status filter, e.g. IN_SCOPE or OUT_OF_SCOPE. "
                    "Omit to list all requirements.",
                }
            },
            "additionalProperties": False,
        },
    ),
    ToolSpec(
        name="get_requirement_detail",
        description=(
            "Fetch one requirement by its key (for example REQ-014), including its description, "
            "acceptance criteria and recorded delivery records. Use after list_requirements when a "
            "specific requirement is central to the question."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "requirement_key": {"type": "string", "description": "The requirement key, e.g. REQ-014."}
            },
            "required": ["requirement_key"],
            "additionalProperties": False,
        },
    ),
]

TOOL_NAMES: frozenset[str] = frozenset(spec.name for spec in TOOL_SPECS)


@dataclass
class ToolExecutionContext:
    """Per-run state for tool dispatch: scope, budget, and the evidence the
    loop has gathered so far."""

    session: AsyncSession
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    limits: RunLimits
    embedder: EmbedderClient
    call_counts: dict[str, int] = field(default_factory=dict)
    collected: dict[uuid.UUID, EvidenceCandidate] = field(default_factory=dict)

    @property
    def collected_candidates(self) -> list[EvidenceCandidate]:
        return list(self.collected.values())

    async def execute(self, call: ToolCall) -> ToolResult:
        """Dispatch one model-requested tool call.

        A refused call (unknown name, spent budget) comes back as an
        `is_error` result rather than an exception so the loop can hand the
        refusal to the model and let it try something else - but the
        refusal is still counted, so refusals cannot buy extra turns.
        """
        handler = _REGISTRY.get(call.name)
        if handler is None:
            return ToolResult(
                call_id=call.call_id,
                name=call.name,
                content=(
                    f"Error: '{call.name}' is not an available tool. "
                    f"Available tools: {', '.join(sorted(TOOL_NAMES))}."
                ),
                is_error=True,
            )

        count = self.call_counts.get(call.name, 0) + 1
        self.call_counts[call.name] = count
        if count > self.limits.max_calls_per_tool:
            return ToolResult(
                call_id=call.call_id,
                name=call.name,
                content=(
                    f"Error: the call budget for '{call.name}' "
                    f"({self.limits.max_calls_per_tool} per run) is exhausted. "
                    "Answer using the evidence you already have, and state explicitly what "
                    "remains unverified."
                ),
                is_error=True,
            )

        try:
            content = await handler(self, call.arguments)
        except ToolInvocationError:
            raise
        except Exception as exc:  # noqa: BLE001 - surfaced to the model, not swallowed
            return ToolResult(
                call_id=call.call_id, name=call.name, content=f"Error running {call.name}: {exc}", is_error=True
            )

        return ToolResult(call_id=call.call_id, name=call.name, content=content)

    def assert_allowed(self, name: str) -> None:
        """Hard allowlist check for callers that dispatch outside `execute`."""
        if name not in TOOL_NAMES:
            raise ToolInvocationError(f"tool '{name}' is not in the run allowlist")
        if self.call_counts.get(name, 0) >= self.limits.max_calls_per_tool:
            raise ToolBudgetExceededError(f"tool '{name}' has exhausted its per-run call budget")


def _truncate(text: str, limit: int = _MAX_CONTENT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... [truncated, {len(text) - limit} more characters]"


async def _search_evidence(ctx: ToolExecutionContext, args: dict[str, Any]) -> str:
    query = str(args.get("query", "")).strip()
    if not query:
        return "Error: 'query' is required and must be a non-empty string."

    raw_limit = args.get("limit", 10)
    limit = raw_limit if isinstance(raw_limit, int) and raw_limit > 0 else 10
    limit = min(limit, _MAX_SEARCH_LIMIT)

    query_embedding = await ctx.embedder.embed_query(query)
    candidates = await hybrid_candidates(
        ctx.session,
        tenant_id=ctx.tenant_id,
        project_id=ctx.project_id,
        query_text=query,
        query_embedding=query_embedding,
        limit=limit,
    )
    for candidate in candidates:
        ctx.collected.setdefault(candidate.evidence_chunk_id, candidate)

    if not candidates:
        return (
            f"No evidence matched '{query}' in this project. "
            "This means nothing indexed addresses it - it is not proof the answer is no."
        )

    lines = [f"{len(candidates)} excerpt(s) matched '{query}':", ""]
    for candidate in candidates[:limit]:
        location_bits = []
        if candidate.location.page_number:
            location_bits.append(f"page {candidate.location.page_number}")
        if candidate.location.section_path:
            location_bits.append(f"section {candidate.location.section_path}")
        location = f" ({', '.join(location_bits)})" if location_bits else ""
        lines.append(f"evidence_chunk_id: {candidate.evidence_chunk_id}{location}")
        lines.append(_truncate(candidate.content))
        lines.append("")
    return "\n".join(lines)


async def _list_project_sources(ctx: ToolExecutionContext, args: dict[str, Any]) -> str:
    repo = SourceRecordRepository(ctx.session, tenant_id=ctx.tenant_id)
    records = await repo.list_for_project(project_id=ctx.project_id)
    if not records:
        return "This project has no indexed source documents yet."

    lines = [f"{len(records)} source document(s) in this project:", ""]
    for record in records:
        title = record.title or "(untitled)"
        lines.append(f"- {title} [type={record.record_type}, source_record_id={record.id}]")
    return "\n".join(lines)


async def _list_requirements(ctx: ToolExecutionContext, args: dict[str, Any]) -> str:
    repo = RequirementRepository(ctx.session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)

    raw_status = args.get("status")
    wanted = raw_status.strip().upper() if isinstance(raw_status, str) and raw_status.strip() else None
    # Filtered in SQL rather than in Python so the scoped query stays the
    # single place a project boundary is applied.
    requirements = await repo.list_for_project(status=wanted)
    if wanted is not None and not requirements:
        return f"No requirements in this project have status {wanted}."

    if not requirements:
        return "This project has no tracked requirements."

    lines = [f"{len(requirements)} requirement(s):", ""]
    for req in requirements:
        lines.append(f"- {req.key}: {req.title} [scope={req.status}, delivery={req.task_status}]")
    return "\n".join(lines)


async def _get_requirement_detail(ctx: ToolExecutionContext, args: dict[str, Any]) -> str:
    key = str(args.get("requirement_key", "")).strip()
    if not key:
        return "Error: 'requirement_key' is required."

    repo = RequirementRepository(ctx.session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    requirement = await repo.get_by_key(key)
    if requirement is None:
        return f"No requirement with key '{key}' exists in this project."

    lines = [
        f"{requirement.key}: {requirement.title}",
        f"scope status: {requirement.status}",
        f"delivery status: {requirement.task_status}",
        f"priority: {requirement.priority}",
    ]
    if requirement.description:
        lines.append(f"description: {_truncate(requirement.description)}")
    if requirement.acceptance_criteria:
        lines.append("acceptance criteria:")
        lines.extend(f"  - {criterion}" for criterion in requirement.acceptance_criteria)
    return "\n".join(lines)


_Handler = Callable[[ToolExecutionContext, dict[str, Any]], Awaitable[str]]

_REGISTRY: dict[str, _Handler] = {
    "search_evidence": _search_evidence,
    "list_project_sources": _list_project_sources,
    "list_requirements": _list_requirements,
    "get_requirement_detail": _get_requirement_detail,
}
