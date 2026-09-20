"""End-to-end agent pipeline against a real database.

This is the test that answers "does the agent actually work?" without an
API key. Only two things are faked, and both are network boundaries:

*   the Anthropic HTTP call (`AnthropicGateway.complete_structured` and
    `ToolLoopGateway._create`), and
*   the embedder HTTP call (`EmbedderClient.embed_query`).

Everything between them is the real system. The INVESTIGATE loop really
dispatches through `ToolExecutionContext.execute`, which really runs
`search_evidence` as a project-scoped hybrid query against Postgres and
pgvector. RERANK really scores the rows that come back. ANALYZE really
reconciles the model's citations against the retrieved packet. VERIFY
really re-checks them, and FINDING really writes `findings` and
`finding_citations` rows.

So a passing run here means the pipeline produces a genuine, cited finding
from genuine evidence, and the only unexercised part is the model's own
judgement. That is deliberately the one thing a test cannot assert
anyway - measuring answer quality is what the evaluation harness in
`packages/evaluation` is for, and that one does need a real key.

The fake model is written to behave like a well-behaved real one: it reads
the evidence chunk ids out of the prompt it is given and cites them back,
exactly as the real prompt instructs. `test_hallucinated_citation_fails_the_run`
then makes it misbehave, to prove the guarantee holds when it does.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

import pytest
from _helpers import create_project, register
from httpx import AsyncClient
from sqlalchemy import select

from ai_atlas.agent_runner.runner import AgentRunner
from atlasai_db.engine import get_async_sessionmaker
from atlasai_db.models.evidence import EvidenceChunk
from atlasai_db.models.findings import Finding, FindingCitation
from atlasai_db.repositories.agent import AgentRunRepository, AgentStepRepository
from atlasai_db.repositories.connectors import ConnectorRepository, ConnectorScopeRepository
from atlasai_db.repositories.evidence import (
    EvidenceChunkRepository,
    SourceRecordRepository,
    SourceVersionRepository,
)
from atlasai_db.settings import EMBEDDING_DIMENSION
from atlasai_domain.agent.contracts import ClassifyOutput
from atlasai_domain.enums import AgentRunIntent, FindingStatus
from atlasai_llm_gateway.client import AnthropicGateway, StructuredCompletion
from atlasai_llm_gateway.cost_tracking import TokenUsage
from atlasai_llm_gateway.schemas import CitationDraft, FindingLLMOutput
from atlasai_llm_gateway.tool_loop import ToolLoopGateway
from atlasai_retrieval.embedder_client import EmbedderClient

# A fixed unit vector. Every chunk and every query embeds to the same
# value, so pgvector's cosine distance runs for real but ranks purely on
# the lexical side - which is what we want when asserting plumbing rather
# than semantic quality.
_FIXED_EMBEDDING = [0.0] * (EMBEDDING_DIMENSION - 1) + [1.0]

_SOW_TEXT = (
    "Statement of Work - Client Portal Revamp, Phase 1. Signed January 15, 2026. "
    "Phase 1 includes single sign-on (SSO) integration with the client's identity provider "
    "and self-service password reset."
)
_EXCLUSION_TEXT = (
    "Statement of Work - Phase 1 exclusions. Multi-factor hardware token support is "
    "explicitly excluded from Phase 1 and deferred to Phase 2."
)

_CHUNK_ID_RE = re.compile(r'evidence_chunk_id="([0-9a-fA-F-]{36})"')


class _FakeBlock:
    def __init__(self, **kw: Any) -> None:
        self.__dict__.update(kw)


class _FakeUsage:
    input_tokens = 120
    output_tokens = 40


class _FakeResponse:
    def __init__(self, *, stop_reason: str, content: list[Any]) -> None:
        self.stop_reason = stop_reason
        self.content = content
        self.model = "fake-model"
        self.usage = _FakeUsage()
        self.stop_details = None


async def _seed_evidence(session: Any, *, tenant_id: uuid.UUID, project_id: uuid.UUID) -> list[uuid.UUID]:
    """Create two evidence chunks reachable from `project_id` through the
    same connector-scope join path production uses."""
    connector = await ConnectorRepository(session, tenant_id=tenant_id).create(
        provider="MANUAL_UPLOAD", credential_ref="manual", external_account_id="manual"
    )
    await ConnectorScopeRepository(session).add(
        connector_id=connector.id,
        project_id=project_id,
        scope_type="upload",
        scope_external_id=None,
        scope_json={},
    )
    record = await SourceRecordRepository(session, tenant_id=tenant_id).create(
        connector_id=connector.id,
        external_id=f"sow-{uuid.uuid4().hex[:8]}",
        record_type="DOCUMENT",
        title="Statement of Work",
        canonical_url=None,
    )
    version = await SourceVersionRepository(session).create(
        source_record_id=record.id,
        version_key="v1",
        content_hash=uuid.uuid4().hex,
        raw_object_uri=None,
        extracted_text_uri=None,
    )
    chunks = [
        EvidenceChunk(
            tenant_id=tenant_id,
            source_version_id=version.id,
            chunk_index=i,
            content=text,
            embedding=_FIXED_EMBEDDING,
            embedding_model="test-fixed",
        )
        for i, text in enumerate([_SOW_TEXT, _EXCLUSION_TEXT])
    ]
    created = await EvidenceChunkRepository(session, tenant_id=tenant_id).bulk_create(chunks)
    await session.commit()
    return [c.id for c in created]


def _install_fakes(monkeypatch: pytest.MonkeyPatch, *, cite: str = "real") -> dict[str, int]:
    """Patch only the two network boundaries. `cite="hallucinated"` makes
    the fake model cite a chunk id that was never retrieved."""
    counters = {"tool_turns": 0, "structured_calls": 0}

    async def fake_embed_query(self: EmbedderClient, text: str) -> list[float]:
        return list(_FIXED_EMBEDDING)

    async def fake_aclose(self: Any) -> None:
        return None

    monkeypatch.setattr(EmbedderClient, "embed_query", fake_embed_query)
    monkeypatch.setattr(EmbedderClient, "aclose", fake_aclose)
    monkeypatch.setattr(ToolLoopGateway, "aclose", fake_aclose)
    monkeypatch.setattr(AnthropicGateway, "aclose", fake_aclose)

    async def fake_create(self: ToolLoopGateway, **kwargs: Any) -> Any:
        """Turn 1: ask for a search. Turn 2: stop. This is the shape of a
        real loop, so ToolExecutionContext.execute really runs the tool."""
        counters["tool_turns"] += 1
        if counters["tool_turns"] == 1:
            return _FakeResponse(
                stop_reason="tool_use",
                content=[
                    _FakeBlock(
                        type="tool_use",
                        id="toolu_fake_1",
                        name="search_evidence",
                        input={"query": "single sign-on Phase 1"},
                    )
                ],
            )
        return _FakeResponse(
            stop_reason="end_turn",
            content=[_FakeBlock(type="text", text="Searched for SSO in Phase 1 scope.")],
        )

    monkeypatch.setattr(ToolLoopGateway, "_create", fake_create)

    async def fake_structured(
        self: AnthropicGateway, *, system: str, user_content: str, output_format: type, **kw: Any
    ) -> StructuredCompletion:
        counters["structured_calls"] += 1
        usage = TokenUsage(model="fake-model", input_tokens=100, output_tokens=25)

        if output_format is ClassifyOutput:
            parsed: Any = ClassifyOutput(
                intent=AgentRunIntent.SCOPE_QUESTION,
                risk_level="MEDIUM",
                rationale="Asks whether a feature is within the signed Phase 1 scope.",
            )
        else:
            # Behave like a real model: copy chunk ids out of the prompt.
            found = _CHUNK_ID_RE.findall(user_content)
            assert found, "the evidence packet reached the model with no chunk ids"
            cited = uuid.uuid4() if cite == "hallucinated" else uuid.UUID(found[0])
            parsed = FindingLLMOutput(
                status=FindingStatus.IN_SCOPE_SUPPORTED,
                summary="Single sign-on is included in Phase 1 per the signed statement of work.",
                facts=["The Phase 1 statement of work lists single sign-on integration."],
                inferences=[],
                citations=[CitationDraft(evidence_chunk_id=cited, citation_label="E1", quote="single sign-on")],
                confidence=0.9,
                recommended_next_step="No further action; the scope is documented.",
                requires_human_review=False,
            )
        return StructuredCompletion(parsed=parsed, usage=usage, model="fake-model", prompt_version="v1")

    monkeypatch.setattr(AnthropicGateway, "complete_structured", fake_structured)
    return counters


async def _setup_run(client: AsyncClient, unique_email: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, list[uuid.UUID]]:
    owner = await register(client, email=unique_email)
    project = await create_project(client, owner=owner, name="Agent Pipeline Project")
    tenant_id = uuid.UUID(owner["tenant_id"])
    project_id = uuid.UUID(project["id"])
    user_id = uuid.UUID(owner["user_id"])

    session_factory = get_async_sessionmaker()
    async with session_factory() as session:
        chunk_ids = await _seed_evidence(session, tenant_id=tenant_id, project_id=project_id)
    return tenant_id, project_id, user_id, chunk_ids


async def test_agent_run_produces_a_real_cited_finding(
    client: AsyncClient, unique_email: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The headline assertion: a completed run, a persisted finding, and a
    citation pointing at a chunk that genuinely exists in the database."""
    tenant_id, project_id, user_id, chunk_ids = await _setup_run(client, unique_email)
    counters = _install_fakes(monkeypatch)

    session_factory = get_async_sessionmaker()
    async with session_factory() as session:
        run = await AgentRunRepository(session, tenant_id=tenant_id, project_id=project_id).create(
            requested_by=user_id, question="Is single sign-on included in Phase 1?"
        )
        await session.commit()
        run_id = run.id

    async with session_factory() as session:
        runner = AgentRunner(session, tenant_id=tenant_id, project_id=project_id)
        result = await runner.run(run_id)

    assert result.status == "COMPLETED", f"run failed: {result.error_json}"
    assert result.intent == AgentRunIntent.SCOPE_QUESTION.value

    async with session_factory() as session:
        findings = (
            (await session.execute(select(Finding).where(Finding.agent_run_id == run_id))).scalars().all()
        )
        assert len(findings) == 1, "exactly one finding should be persisted"
        finding = findings[0]
        assert finding.status == FindingStatus.IN_SCOPE_SUPPORTED.value
        assert finding.summary

        citations = (
            (await session.execute(select(FindingCitation).where(FindingCitation.finding_id == finding.id)))
            .scalars()
            .all()
        )
        assert citations, "a supported finding must carry at least one citation"
        for citation in citations:
            assert citation.evidence_chunk_id in chunk_ids, "citation points at a chunk that was never retrieved"
            # The cited chunk must still be a live row, not a dangling id.
            chunk = await session.get(EvidenceChunk, citation.evidence_chunk_id)
            assert chunk is not None and chunk.deleted_at is None

    # The loop really ran: two turns, and the model never saw the database.
    assert counters["tool_turns"] == 2
    assert counters["structured_calls"] == 2  # CLASSIFY + ANALYZE


async def test_investigate_really_dispatches_tools_and_checkpoints_them(
    client: AsyncClient, unique_email: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INVESTIGATE must leave an auditable trail: a step row per tool call,
    naming the tool, so a reviewer can see what the agent looked for."""
    tenant_id, project_id, user_id, _ = await _setup_run(client, unique_email)
    _install_fakes(monkeypatch)

    session_factory = get_async_sessionmaker()
    async with session_factory() as session:
        run = await AgentRunRepository(session, tenant_id=tenant_id, project_id=project_id).create(
            requested_by=user_id, question="Is single sign-on included in Phase 1?"
        )
        await session.commit()
        run_id = run.id

    async with session_factory() as session:
        await AgentRunner(session, tenant_id=tenant_id, project_id=project_id).run(run_id)

    async with session_factory() as session:
        steps = await AgentStepRepository(session).list_from(run_id)

    states = [s.state_name for s in steps]
    assert "INVESTIGATE" in states, f"INVESTIGATE never ran; states were {states}"
    assert "FINDING" in states

    tool_steps = [s for s in steps if s.tool_name == "search_evidence"]
    assert tool_steps, "the search_evidence call was not checkpointed"
    assert tool_steps[0].input_json == {"query": "single sign-on Phase 1"}

    # Step numbers are unique and ordered - the run is replayable.
    step_numbers = [s.step_no for s in steps]
    assert step_numbers == sorted(step_numbers)
    assert len(step_numbers) == len(set(step_numbers))


async def test_hallucinated_citation_fails_the_run_instead_of_persisting_it(
    client: AsyncClient, unique_email: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The core product guarantee, end to end. When the model cites a chunk
    that was never retrieved, the run must FAIL and write nothing - never
    downgrade to a finding with a bad citation attached."""
    tenant_id, project_id, user_id, _ = await _setup_run(client, unique_email)
    _install_fakes(monkeypatch, cite="hallucinated")

    session_factory = get_async_sessionmaker()
    async with session_factory() as session:
        run = await AgentRunRepository(session, tenant_id=tenant_id, project_id=project_id).create(
            requested_by=user_id, question="Is single sign-on included in Phase 1?"
        )
        await session.commit()
        run_id = run.id

    async with session_factory() as session:
        result = await AgentRunner(session, tenant_id=tenant_id, project_id=project_id).run(run_id)

    assert result.status == "FAILED"
    assert result.error_json is not None
    assert "not present in the retrieved evidence packet" in str(result.error_json)

    async with session_factory() as session:
        findings = (
            (await session.execute(select(Finding).where(Finding.agent_run_id == run_id))).scalars().all()
        )
        assert findings == [], "a run with a hallucinated citation must persist no finding"


async def test_evidence_is_scoped_to_the_project_the_run_belongs_to(
    client: AsyncClient, unique_email: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second project in the same tenant has its own evidence. The run
    must only ever see its own project's chunks - scope is applied in the
    query, so the model cannot reach across even in principle."""
    owner = await register(client, email=unique_email)
    tenant_id = uuid.UUID(owner["tenant_id"])
    user_id = uuid.UUID(owner["user_id"])

    project_a = uuid.UUID((await create_project(client, owner=owner, name="Project A"))["id"])
    project_b = uuid.UUID((await create_project(client, owner=owner, name="Project B"))["id"])

    session_factory = get_async_sessionmaker()
    async with session_factory() as session:
        a_chunks = await _seed_evidence(session, tenant_id=tenant_id, project_id=project_a)
    async with session_factory() as session:
        b_chunks = await _seed_evidence(session, tenant_id=tenant_id, project_id=project_b)

    _install_fakes(monkeypatch)

    async with session_factory() as session:
        run = await AgentRunRepository(session, tenant_id=tenant_id, project_id=project_a).create(
            requested_by=user_id, question="Is single sign-on included in Phase 1?"
        )
        await session.commit()
        run_id = run.id

    async with session_factory() as session:
        result = await AgentRunner(session, tenant_id=tenant_id, project_id=project_a).run(run_id)
    assert result.status == "COMPLETED", f"run failed: {result.error_json}"

    async with session_factory() as session:
        finding = (
            (await session.execute(select(Finding).where(Finding.agent_run_id == run_id))).scalars().one()
        )
        citations = (
            (await session.execute(select(FindingCitation).where(FindingCitation.finding_id == finding.id)))
            .scalars()
            .all()
        )

    cited_ids = {c.evidence_chunk_id for c in citations}
    assert cited_ids, "expected at least one citation"
    assert cited_ids <= set(a_chunks), "the run cited evidence from its own project"
    assert not (cited_ids & set(b_chunks)), "the run reached into another project's evidence"
