"""Per-run context threaded through every step executor: the DB session,
tenant/project scope, the agent_runs row, run limits, and the step
recorder. One instance is built once per run in runner.py and passed to
every step_executors/*.py function.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from ai_atlas.agent_runner.checkpoint import AgentStepRecorder
from atlasai_db.models.agent import AgentRun
from atlasai_domain.agent.limits import RunLimits


@dataclass
class StepContext:
    session: AsyncSession
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    agent_run: AgentRun
    limits: RunLimits
    recorder: AgentStepRecorder
    tool_call_counts: dict[str, int] = field(default_factory=dict)
    total_tokens_used: int = 0

    def register_tool_call(self, tool_name: str) -> int:
        self.tool_call_counts[tool_name] = self.tool_call_counts.get(tool_name, 0) + 1
        return self.tool_call_counts[tool_name]
