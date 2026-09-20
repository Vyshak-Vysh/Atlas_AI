"""Tool-calling contracts for the INVESTIGATE state (ATLASAI_MASTER_SPEC.md §4).

The agent does not get arbitrary code, SQL, shell, or URL access. It gets a
closed registry of read-only, project-scoped tools declared here as data:
each `ToolSpec` carries the JSON Schema the model is shown and a stable
name that the executor resolves against its own allowlist. A model that
emits a name outside the allowlist is refused by `ToolInvocationError`
rather than dispatched — the allowlist is enforced at execution time, not
merely suggested in the prompt.

Budgets (`RunLimits.max_steps`, `RunLimits.max_calls_per_tool`) are counted
over real invocations of these tools, so a model that loops on one tool
runs out of budget and the run terminates deterministically.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    """A single tool as advertised to the model.

    `input_schema` is a JSON Schema object passed verbatim to the provider's
    tool-definition field, so it must stay a plain dict rather than a
    Pydantic model — providers reject unknown keywords that a model dump
    would introduce.
    """

    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=1)
    input_schema: dict[str, Any]

    def to_provider_dict(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


class ToolCall(BaseModel):
    """One tool invocation requested by the model."""

    call_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """The outcome of executing one `ToolCall`.

    `is_error` is surfaced back to the model as a provider-level error
    result so it can recover (try a different query) rather than silently
    receiving an empty success — but a refused tool name or an exhausted
    budget still counts against the run's step budget, so recovery attempts
    cannot extend a run indefinitely.
    """

    call_id: str
    name: str
    content: str
    is_error: bool = False


class ToolInvocationError(Exception):
    """Raised when a model requests a tool outside the run's allowlist, or
    one whose per-run call budget is already spent. Never results in a
    dispatch."""


class ToolBudgetExceededError(ToolInvocationError):
    """A specific `ToolInvocationError`: the tool is legitimate, but this
    run has already called it `RunLimits.max_calls_per_tool` times."""
