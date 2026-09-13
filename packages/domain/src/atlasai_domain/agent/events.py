"""Realtime agent-step event shape (implementation plan §4 "Realtime").

Published to Redis channel `agent_run:{run_id}:events` by
apps/ai_atlas/agent_runner/checkpoint.py after each agent_steps row is
committed, and consumed by apps/api's SSE endpoint. Deliberately small and
non-sensitive — never raw evidence text, prompts, or secrets — since this
payload crosses a process boundary and is streamed straight to a browser.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AgentStepEvent(BaseModel):
    run_id: str
    step_no: int
    state_name: str
    status: str
    tool_name: str | None = None
    summary: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
