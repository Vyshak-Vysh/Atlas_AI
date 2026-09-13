from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.deps import ProjectContext, get_db_session, require_project_membership_query
from atlasai_api.schemas.requirements import (
    CreateRequirementRequest,
    DeliveryRecordResponse,
    RequirementDetailResponse,
    RequirementEvidenceLinkResponse,
    RequirementResponse,
)
from atlasai_db.exceptions import NotFoundError
from atlasai_db.repositories.requirements import RequirementRepository
from atlasai_domain.enums import MembershipRole, RequirementStatus

router = APIRouter(prefix="/api/v1/requirements", tags=["requirements"])

_REQUIREMENT_WRITER_ROLES = {MembershipRole.PROJECT_MANAGER, MembershipRole.AI_ENGINEER_ADMIN}


@router.get("", response_model=list[RequirementResponse])
async def list_requirements(
    status_filter: str | None = Query(default=None, alias="status"),
    phase_id: uuid.UUID | None = Query(default=None),
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> list[RequirementResponse]:
    repo = RequirementRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    requirements = await repo.list_for_project(status=status_filter, phase_id=phase_id)
    return [RequirementResponse.model_validate(r) for r in requirements]


@router.post("", response_model=RequirementResponse, status_code=status.HTTP_201_CREATED)
async def create_requirement(
    body: CreateRequirementRequest,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> RequirementResponse:
    if ctx.role not in _REQUIREMENT_WRITER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot create requirements")

    try:
        req_status = RequirementStatus(body.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid status") from exc

    repo = RequirementRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    if await repo.get_by_key(body.key) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="a requirement with this key already exists")

    requirement = await repo.create(
        key=body.key,
        title=body.title,
        status=req_status.value,
        phase_id=body.phase_id,
        description=body.description,
        acceptance_criteria=body.acceptance_criteria,
    )
    await session.commit()
    return RequirementResponse.model_validate(requirement)


@router.get("/{requirement_id}", response_model=RequirementDetailResponse)
async def get_requirement(
    requirement_id: uuid.UUID,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> RequirementDetailResponse:
    repo = RequirementRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    try:
        requirement = await repo.get_with_relations(requirement_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="requirement not found") from exc

    return RequirementDetailResponse(
        requirement=RequirementResponse.model_validate(requirement),
        evidence_links=[
            RequirementEvidenceLinkResponse(
                evidence_chunk_id=link.evidence_chunk_id,
                relation_type=link.relation_type,
                confidence=float(link.confidence) if link.confidence is not None else None,
                rationale=link.rationale,
            )
            for link in requirement.evidence_links
        ],
        delivery_records=[DeliveryRecordResponse.model_validate(record) for record in requirement.delivery_records],
    )
