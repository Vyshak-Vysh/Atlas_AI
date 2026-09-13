"""Evaluation harness: runs EvalCase fixtures through the real
`POST /api/v1/agent/runs` HTTP path (TD_v2.md §9 "no shadow path") against
a running AtlasAI stack, tagging everything under a dedicated eval
tenant/project per case rather than inventing a parallel evaluation
schema (see the implementation plan's "Evaluation" section — ADR-0006).

Requires a reachable API base_url with a working ANTHROPIC_API_KEY behind
it; this module makes real HTTP calls and does not mock the LLM.
"""

from __future__ import annotations

import asyncio
import time
import uuid

import httpx

from atlasai_evaluation.metrics import EvalCaseResult, EvalReport, expected_status_matches
from atlasai_evaluation.schema import EvalCase, EvalCategory

_POLL_INTERVAL_SECONDS = 2.0
_RUN_TIMEOUT_SECONDS = 120.0


class EvalHarness:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def run_all(self, cases: list[EvalCase]) -> EvalReport:
        report = EvalReport()
        for case in cases:
            if case.category == EvalCategory.PERMISSION_BOUNDARY:
                report.results.append(await self._run_permission_boundary_case(case))
            else:
                report.results.append(await self._run_standard_case(case))
        return report

    async def _run_standard_case(self, case: EvalCase) -> EvalCaseResult:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30.0) as client:
            suffix = uuid.uuid4().hex[:10]
            reg = await client.post(
                "/api/v1/auth/register",
                json={
                    "tenant_name": f"Eval {case.id} {suffix}",
                    "email": f"eval-{case.id}-{suffix}@atlasai-eval.dev",
                    "password": "evaluation-harness-password-1",
                    "display_name": "Eval Harness",
                },
            )
            if reg.status_code != 201:
                return EvalCaseResult(
                    case_id=case.id, category=case.category, passed=False, detail=f"registration failed: {reg.text}"
                )
            tokens = reg.json()
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            tenant_id = tokens["tenant_id"]

            proj = await client.post(
                "/api/v1/projects", json={"tenant_id": tenant_id, "name": f"Eval {case.id}"}, headers=headers
            )
            if proj.status_code != 201:
                return EvalCaseResult(
                    case_id=case.id,
                    category=case.category,
                    passed=False,
                    detail=f"project creation failed: {proj.text}",
                )
            project_id = proj.json()["id"]

            for evidence in case.evidence:
                files = {"file": (evidence.filename, evidence.text_content.encode("utf-8"), evidence.mime_type)}
                upload = await client.post(
                    "/api/v1/documents/upload", data={"project_id": project_id}, files=files, headers=headers
                )
                if upload.status_code != 201:
                    return EvalCaseResult(
                        case_id=case.id, category=case.category, passed=False,
                        detail=f"evidence upload failed: {upload.text}",
                    )
                source_id = upload.json()["source_record_id"]
                await self._wait_for_ingestion(client, source_id, project_id, headers)

            run = await client.post(
                "/api/v1/agent/runs",
                params={"project_id": project_id},
                json={"project_id": project_id, "question": case.question},
                headers=headers,
            )
            if run.status_code != 202:
                return EvalCaseResult(
                    case_id=case.id,
                    category=case.category,
                    passed=False,
                    detail=f"agent run creation failed: {run.text}",
                )
            run_id = run.json()["id"]

            final_run = await self._wait_for_run(client, run_id, project_id, headers)
            if final_run["status"] != "COMPLETED" or not final_run.get("finding_id"):
                return EvalCaseResult(
                    case_id=case.id, category=case.category, passed=False,
                    detail=f"run did not complete: {final_run}",
                )

            finding = await client.get(
                f"/api/v1/findings/{final_run['finding_id']}", params={"project_id": project_id}, headers=headers
            )
            finding_body = finding.json()
            actual_status = finding_body["status"]
            passed = expected_status_matches(case, actual_status) and (
                case.expect_requires_human_review is None
                or finding_body["requires_human_review"] == case.expect_requires_human_review
            )
            return EvalCaseResult(
                case_id=case.id,
                category=case.category,
                passed=passed,
                actual_status=actual_status,
                actual_requires_human_review=finding_body["requires_human_review"],
                citation_count=len(finding_body["citations"]),
                fact_count=len(finding_body["facts"]),
            )

    async def _run_permission_boundary_case(self, case: EvalCase) -> EvalCaseResult:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30.0) as client:
            suffix = uuid.uuid4().hex[:10]
            owner_reg = await client.post(
                "/api/v1/auth/register",
                json={
                    "tenant_name": f"Eval owner {suffix}",
                    "email": f"eval-owner-{suffix}@atlasai-eval.dev",
                    "password": "evaluation-harness-password-1",
                    "display_name": "Eval Owner",
                },
            )
            owner_tokens = owner_reg.json()
            owner_headers = {"Authorization": f"Bearer {owner_tokens['access_token']}"}
            proj = await client.post(
                "/api/v1/projects",
                json={"tenant_id": owner_tokens["tenant_id"], "name": f"Eval boundary {case.id}"},
                headers=owner_headers,
            )
            project_id = proj.json()["id"]

            intruder_reg = await client.post(
                "/api/v1/auth/register",
                json={
                    "tenant_name": f"Eval intruder {suffix}",
                    "email": f"eval-intruder-{suffix}@atlasai-eval.dev",
                    "password": "evaluation-harness-password-1",
                    "display_name": "Eval Intruder",
                },
            )
            intruder_headers = {"Authorization": f"Bearer {intruder_reg.json()['access_token']}"}

            denied = await client.get(
                f"/api/v1/projects/{project_id}/overview", headers=intruder_headers
            )
            passed = denied.status_code == 404
            return EvalCaseResult(
                case_id=case.id,
                category=case.category,
                passed=passed,
                detail=None if passed else f"expected 404, got {denied.status_code}",
            )

    async def _wait_for_ingestion(
        self, client: httpx.AsyncClient, source_id: str, project_id: str, headers: dict[str, str]
    ) -> None:
        deadline = time.monotonic() + _RUN_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            resp = await client.get(f"/api/v1/sources/{source_id}", params={"project_id": project_id}, headers=headers)
            if resp.json().get("ingestion_status") == "READY":
                return
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        raise TimeoutError(f"source {source_id} did not finish ingestion in time")

    async def _wait_for_run(
        self, client: httpx.AsyncClient, run_id: str, project_id: str, headers: dict[str, str]
    ) -> dict[str, object]:
        deadline = time.monotonic() + _RUN_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            resp = await client.get(f"/api/v1/agent/runs/{run_id}", params={"project_id": project_id}, headers=headers)
            body: dict[str, object] = resp.json()
            if body["status"] in {"COMPLETED", "FAILED", "WAITING_APPROVAL"}:
                return body
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        raise TimeoutError(f"agent run {run_id} did not finish in time")
