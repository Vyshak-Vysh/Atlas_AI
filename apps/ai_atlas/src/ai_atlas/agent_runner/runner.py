"""AgentRunner: drives one agent_runs row through the bounded state machine
(ATLASAI_MASTER_SPEC.md §4):

    RECEIVED -> CLASSIFY -> PLAN -> RETRIEVE -> RERANK -> ANALYZE
    -> VERIFY -> FINDING -> ACTION_DECISION -> COMPLETE

Bounded by RunLimits (max 12 steps, max 3 calls/tool, a hard run timeout,
a token budget) — any state can fail into FAILED, which is always audited
and never leaves the run silently stuck. The action branch
(PROPOSE_ACTION -> WAIT_APPROVAL -> EXECUTE) is reachable in the domain's
transition table but not entered autonomously by this build (see
step_executors/action_decision.py).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ai_atlas.agent_runner.checkpoint import AgentStepRecorder
from ai_atlas.agent_runner.context import StepContext
from ai_atlas.agent_runner.step_executors import (
    action_decision,
    analyze,
    classify,
    finding,
    plan,
    propose_action,
    rerank,
    retrieve,
    verify,
)
from atlasai_db.models.agent import AgentRun
from atlasai_db.repositories.agent import AgentRunRepository
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_domain.agent.limits import RunLimits
from atlasai_domain.enums import AuditEventType


class StepBudgetExceededError(Exception):
    pass


class AgentRunner:
    def __init__(self, session: AsyncSession, *, tenant_id: uuid.UUID, project_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._project_id = project_id

    async def run(self, agent_run_id: uuid.UUID, *, limits: RunLimits | None = None) -> AgentRun:
        run_repo = AgentRunRepository(self._session, tenant_id=self._tenant_id, project_id=self._project_id)
        audit_repo = AuditEventRepository(self._session, tenant_id=self._tenant_id)
        agent_run = await run_repo.get_by_id(agent_run_id)
        effective_limits = self._resolve_limits(base=limits or RunLimits(), model_policy=agent_run.model_policy)

        ctx = StepContext(
            session=self._session,
            tenant_id=self._tenant_id,
            project_id=self._project_id,
            agent_run=agent_run,
            limits=effective_limits,
            recorder=AgentStepRecorder(self._session, agent_run_id=agent_run_id),
        )

        await run_repo.mark_started(agent_run)
        await self._session.commit()
        await audit_repo.record(
            event_type=AuditEventType.AGENT_RUN_STARTED,
            actor_id=agent_run.requested_by,
            target_type="agent_run",
            target_id=agent_run.id,
        )
        await self._session.commit()

        try:
            await asyncio.wait_for(self._run_states(ctx), timeout=effective_limits.run_timeout_seconds)
        except Exception as exc:  # noqa: BLE001 — every failure path must mark FAILED and audit it
            await self._fail(run_repo, audit_repo, agent_run, exc)
            return agent_run

        agent_run.state_json = {**agent_run.state_json, "total_tokens_used": ctx.total_tokens_used}

        if agent_run.status == "WAITING_APPROVAL":
            # _run_states already set this and returned early — the run is
            # paused pending a human decision, not complete. See
            # step_executors/propose_action.py and action_service.py.
            await self._session.commit()
            return agent_run

        await run_repo.mark_finished(agent_run, status="COMPLETED")
        await audit_repo.record(
            event_type=AuditEventType.AGENT_RUN_COMPLETED,
            actor_id=agent_run.requested_by,
            target_type="agent_run",
            target_id=agent_run.id,
            metadata={"total_tokens_used": ctx.total_tokens_used},
        )
        await self._session.commit()
        return agent_run

    async def _run_states(self, ctx: StepContext) -> None:
        question = ctx.agent_run.question
        step_count = 0

        def check_budget() -> None:
            nonlocal step_count
            step_count += 1
            if step_count > ctx.limits.max_steps:
                raise StepBudgetExceededError(f"agent run exceeded its budget of {ctx.limits.max_steps} steps")

        check_budget()
        await ctx.recorder.record(
            state_name="RECEIVED", status="SUCCEEDED", started_at=datetime.now(UTC), summary="run accepted"
        )

        check_budget()
        classify_output = await classify.run(ctx, question=question)
        ctx.agent_run.intent = classify_output.intent.value

        check_budget()
        plan_output = await plan.run(ctx, question=question)

        check_budget()
        retrieve_outputs = await retrieve.run(ctx, plan=plan_output)

        check_budget()
        rerank_output = await rerank.run(ctx, question=question, retrieve_outputs=retrieve_outputs)

        check_budget()
        draft_finding, _completion = await analyze.run(ctx, question=question, ranked_candidates=rerank_output.ranked)

        check_budget()
        await verify.run(ctx, finding=draft_finding, ranked_candidates=rerank_output.ranked)

        check_budget()
        finding_row = await finding.run(ctx, finding=draft_finding)
        ctx.agent_run.state_json = {**ctx.agent_run.state_json, "finding_id": str(finding_row.id)}

        check_budget()
        decision = await action_decision.run(ctx, classify_output=classify_output, finding=draft_finding)

        if decision.requires_action:
            check_budget()
            action = await propose_action.run(ctx, decision=decision)
            # WAIT_APPROVAL: the run pauses here — a human approval arrives
            # later, out of band, via `POST /api/v1/actions/{id}/approve`
            # (apps/api/services/action_service.py). This Celery task must
            # not block waiting for it.
            ctx.agent_run.status = "WAITING_APPROVAL"
            ctx.agent_run.state_json = {**ctx.agent_run.state_json, "action_id": str(action.id)}
            await ctx.recorder.record(
                state_name="WAIT_APPROVAL",
                status="SUCCEEDED",
                started_at=datetime.now(UTC),
                summary=f"awaiting approval for action {action.id}",
            )
            return

        check_budget()
        await ctx.recorder.record(
            state_name="COMPLETE", status="SUCCEEDED", started_at=datetime.now(UTC), summary="run complete"
        )

    @staticmethod
    def _resolve_limits(*, base: RunLimits, model_policy: dict[str, Any]) -> RunLimits:
        """A run may narrow (never widen) the global defaults via
        agent_runs.model_policy — see RunLimits.narrowed_by."""
        if not model_policy:
            return base
        try:
            return base.narrowed_by(RunLimits(**model_policy))
        except TypeError:
            # Malformed/partial override — fail safe to the unmodified defaults
            # rather than reject the run over a model_policy typo.
            return base

    async def _fail(
        self, run_repo: AgentRunRepository, audit_repo: AuditEventRepository, agent_run: AgentRun, exc: Exception
    ) -> None:
        await run_repo.mark_finished(agent_run, status="FAILED", error_json={"message": str(exc)})
        await audit_repo.record(
            event_type=AuditEventType.AGENT_RUN_FAILED,
            actor_id=agent_run.requested_by,
            target_type="agent_run",
            target_id=agent_run.id,
            metadata={"error": str(exc)},
        )
        await self._session.commit()
