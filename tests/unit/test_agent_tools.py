"""Unit tests for the agent's tool allowlist and per-run call budgets
(ATLASAI_MASTER_SPEC.md §4).

These cover the guarantees that make the tool loop safe to run against a
live model: a tool the registry does not define is never dispatched, and a
tool that is defined cannot be called more times than the run's budget
allows. Both are enforced in `ToolExecutionContext.execute` rather than in
the prompt, so they are testable without an API key or a database.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from ai_atlas.agent_runner.tools import TOOL_NAMES, TOOL_SPECS, ToolExecutionContext
from atlasai_domain.agent.limits import RunLimits
from atlasai_domain.agent.tools import ToolCall, ToolSpec


def _context(*, max_calls_per_tool: int = 3) -> ToolExecutionContext:
    """A context with no session/embedder — the tests below only exercise
    dispatch, allowlisting and budgeting, none of which touch either."""
    return ToolExecutionContext(
        session=None,  # type: ignore[arg-type]
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        limits=RunLimits(max_calls_per_tool=max_calls_per_tool),
        embedder=None,  # type: ignore[arg-type]
    )


def _call(name: str, **arguments: Any) -> ToolCall:
    return ToolCall(call_id=f"toolu_{uuid.uuid4().hex[:8]}", name=name, arguments=arguments)


def test_every_declared_tool_has_a_handler() -> None:
    """A spec advertised to the model with no handler behind it would be a
    guaranteed runtime error the first time the model picked it."""
    ctx = _context()
    for spec in TOOL_SPECS:
        assert spec.name in TOOL_NAMES
        # _REGISTRY is the dispatch table `execute` resolves against.
        from ai_atlas.agent_runner.tools import _REGISTRY

        assert spec.name in _REGISTRY, f"{spec.name} is advertised but has no handler"
    assert len(TOOL_NAMES) == len(TOOL_SPECS), "duplicate tool name in the registry"
    assert ctx.call_counts == {}


@pytest.mark.asyncio
async def test_unknown_tool_is_refused_not_dispatched() -> None:
    ctx = _context()
    result = await ctx.execute(_call("run_sql", query="DROP TABLE tenants"))

    assert result.is_error
    assert "not an available tool" in result.content
    # A refused name must not be recorded as a legitimate call.
    assert "run_sql" not in ctx.call_counts


@pytest.mark.asyncio
async def test_per_tool_call_budget_is_enforced() -> None:
    """The fourth call to a tool budgeted at three is refused, and the
    refusal tells the model to answer with what it has rather than simply
    failing the run."""
    ctx = _context(max_calls_per_tool=3)

    # list_project_sources needs no arguments; stub its handler so the test
    # exercises budgeting rather than the database.
    from ai_atlas.agent_runner import tools as tools_module

    async def _stub(_ctx: ToolExecutionContext, _args: dict[str, Any]) -> str:
        return "ok"

    original = tools_module._REGISTRY["list_project_sources"]
    tools_module._REGISTRY["list_project_sources"] = _stub
    try:
        for _ in range(3):
            result = await ctx.execute(_call("list_project_sources"))
            assert not result.is_error

        exhausted = await ctx.execute(_call("list_project_sources"))
    finally:
        tools_module._REGISTRY["list_project_sources"] = original

    assert exhausted.is_error
    assert "budget" in exhausted.content.lower()
    assert ctx.call_counts["list_project_sources"] == 4


@pytest.mark.asyncio
async def test_budget_is_tracked_per_tool_not_globally() -> None:
    """Spending one tool's budget must not starve a different tool."""
    ctx = _context(max_calls_per_tool=1)
    from ai_atlas.agent_runner import tools as tools_module

    async def _stub(_ctx: ToolExecutionContext, _args: dict[str, Any]) -> str:
        return "ok"

    originals = dict(tools_module._REGISTRY)
    for name in ("list_project_sources", "list_requirements"):
        tools_module._REGISTRY[name] = _stub
    try:
        assert not (await ctx.execute(_call("list_project_sources"))).is_error
        assert (await ctx.execute(_call("list_project_sources"))).is_error
        # Different tool, untouched budget.
        assert not (await ctx.execute(_call("list_requirements"))).is_error
    finally:
        tools_module._REGISTRY.clear()
        tools_module._REGISTRY.update(originals)


@pytest.mark.asyncio
async def test_handler_exception_becomes_an_error_result_not_a_crash() -> None:
    """A failing tool must come back to the model as a recoverable error so
    it can try something else, rather than aborting the whole run."""
    ctx = _context()
    from ai_atlas.agent_runner import tools as tools_module

    async def _boom(_ctx: ToolExecutionContext, _args: dict[str, Any]) -> str:
        raise RuntimeError("embedder unreachable")

    original = tools_module._REGISTRY["search_evidence"]
    tools_module._REGISTRY["search_evidence"] = _boom
    try:
        result = await ctx.execute(_call("search_evidence", query="sso"))
    finally:
        tools_module._REGISTRY["search_evidence"] = original

    assert result.is_error
    assert "embedder unreachable" in result.content


def test_no_tool_accepts_a_tenant_or_project_argument() -> None:
    """Scope comes from the run, never from the model. A tool that let the
    model name its own tenant or project would be a cross-tenant read."""
    forbidden = {"tenant_id", "project_id", "tenant", "project"}
    for spec in TOOL_SPECS:
        properties = set(spec.input_schema.get("properties", {}))
        assert not (properties & forbidden), f"{spec.name} exposes a scope argument to the model"


def test_tool_schemas_are_closed() -> None:
    """`additionalProperties: false` keeps a model from smuggling unexpected
    keys past the schema into a handler."""
    for spec in TOOL_SPECS:
        assert spec.input_schema.get("additionalProperties") is False, f"{spec.name} has an open schema"
        assert spec.input_schema.get("type") == "object"


def test_tool_spec_name_pattern_rejects_provider_hostile_names() -> None:
    with pytest.raises(ValueError, match="String should match pattern"):
        ToolSpec(name="Search Evidence", description="x", input_schema={"type": "object"})
