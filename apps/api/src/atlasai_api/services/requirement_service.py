"""Requirement (task) mutation, comment, and history logic.

Extracted into its own service module — mirroring action_service.py's
shape — because unlike the original list/create-only requirements flow,
edits here touch multiple fields, validate an assignee against project
membership, and must emit one audit event per changed field (the entire
"who changed what, when" history mechanism; see AuditEventRepository).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_db.exceptions import ConflictError, NotFoundError
from atlasai_db.models.requirements import Requirement, RequirementComment
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_db.repositories.requirements import RequirementCommentRepository, RequirementRepository
from atlasai_db.repositories.tenancy import MembershipRepository, PhaseRepository, SprintRepository
from atlasai_domain.enums import AuditEventType, MembershipRole


class InvalidAssigneeError(Exception):
    """assignee_id does not refer to a current member of this project."""


class InvalidSprintError(Exception):
    """sprint_id does not refer to a sprint in this project."""


class InvalidPhaseError(Exception):
    """phase_id does not refer to a phase in this project."""


class RequirementHasEvidenceError(ConflictError):
    """Refuses to hard-delete a requirement with linked evidence or
    delivery records — that would destroy an audited verification trail,
    which conflicts with this platform's evidence-is-never-silently-lost
    principle. Callers should change task_status instead."""


class CommentPermissionError(Exception):
    """Only a comment's author or an AI_ENGINEER_ADMIN may edit/delete it."""


def _normalize(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


async def update_requirement(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    requirement_id: uuid.UUID,
    actor_id: uuid.UUID,
    changes: dict[str, Any],
) -> Requirement:
    repo = RequirementRepository(session, tenant_id=tenant_id, project_id=project_id)
    requirement = await repo.get_by_id(requirement_id)

    if "assignee_id" in changes and changes["assignee_id"] is not None:
        role = await MembershipRepository(session).get_project_role(
            project_id=project_id, user_id=changes["assignee_id"]
        )
        if role is None:
            raise InvalidAssigneeError("assignee is not a member of this project")

    if "sprint_id" in changes and changes["sprint_id"] is not None:
        try:
            await SprintRepository(session, tenant_id=tenant_id, project_id=project_id).get_by_id(
                changes["sprint_id"]
            )
        except NotFoundError as exc:
            raise InvalidSprintError("sprint is not part of this project") from exc

    if "phase_id" in changes and changes["phase_id"] is not None:
        try:
            await PhaseRepository(session, tenant_id=tenant_id, project_id=project_id).get_by_id(
                changes["phase_id"]
            )
        except NotFoundError as exc:
            raise InvalidPhaseError("phase is not part of this project") from exc

    audit_repo = AuditEventRepository(session, tenant_id=tenant_id)
    for field, new_value in changes.items():
        old_normalized = _normalize(getattr(requirement, field))
        new_normalized = _normalize(new_value)
        if old_normalized == new_normalized:
            continue
        await audit_repo.record(
            event_type=AuditEventType.REQUIREMENT_UPDATED,
            actor_id=actor_id,
            target_type="requirement",
            target_id=requirement.id,
            metadata={"field": field, "old_value": old_normalized, "new_value": new_normalized},
        )

    requirement = await repo.update(requirement, **changes)
    await session.commit()
    return requirement


async def delete_requirement(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    requirement_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> None:
    repo = RequirementRepository(session, tenant_id=tenant_id, project_id=project_id)
    requirement = await repo.get_with_relations(requirement_id)
    if requirement.evidence_links or requirement.delivery_records:
        raise RequirementHasEvidenceError(
            "cannot delete a task with linked evidence or delivery records — change its task_status instead"
        )

    await AuditEventRepository(session, tenant_id=tenant_id).record(
        event_type=AuditEventType.REQUIREMENT_DELETED,
        actor_id=actor_id,
        target_type="requirement",
        target_id=requirement.id,
        metadata={"key": requirement.key, "title": requirement.title},
    )
    await repo.delete(requirement)
    await session.commit()


async def add_comment(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    requirement_id: uuid.UUID,
    actor_id: uuid.UUID,
    body: str,
) -> RequirementComment:
    requirement = await RequirementRepository(session, tenant_id=tenant_id, project_id=project_id).get_by_id(
        requirement_id
    )

    comment = await RequirementCommentRepository(session).create(
        requirement_id=requirement.id, author_id=actor_id, body=body
    )
    await AuditEventRepository(session, tenant_id=tenant_id).record(
        event_type=AuditEventType.REQUIREMENT_COMMENT_ADDED,
        actor_id=actor_id,
        target_type="requirement",
        target_id=requirement.id,
        metadata={"comment_id": str(comment.id)},
    )
    await session.commit()
    return comment


async def _load_own_comment(
    session: AsyncSession, *, requirement_id: uuid.UUID, comment_id: uuid.UUID
) -> RequirementComment:
    comment = await RequirementCommentRepository(session).get_by_id(comment_id)
    if comment.requirement_id != requirement_id:
        raise NotFoundError("RequirementComment", comment_id)
    return comment


def _assert_can_moderate(comment: RequirementComment, *, actor_id: uuid.UUID, actor_role: MembershipRole) -> None:
    if comment.author_id != actor_id and actor_role != MembershipRole.AI_ENGINEER_ADMIN:
        raise CommentPermissionError("only the comment's author or an admin may modify it")


async def update_comment(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    requirement_id: uuid.UUID,
    comment_id: uuid.UUID,
    actor_id: uuid.UUID,
    actor_role: MembershipRole,
    body: str,
) -> RequirementComment:
    await RequirementRepository(session, tenant_id=tenant_id, project_id=project_id).get_by_id(requirement_id)
    comment = await _load_own_comment(session, requirement_id=requirement_id, comment_id=comment_id)
    _assert_can_moderate(comment, actor_id=actor_id, actor_role=actor_role)

    comment = await RequirementCommentRepository(session).update(comment, body=body)
    await AuditEventRepository(session, tenant_id=tenant_id).record(
        event_type=AuditEventType.REQUIREMENT_COMMENT_UPDATED,
        actor_id=actor_id,
        target_type="requirement",
        target_id=requirement_id,
        metadata={"comment_id": str(comment.id)},
    )
    await session.commit()
    return comment


async def delete_comment(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    requirement_id: uuid.UUID,
    comment_id: uuid.UUID,
    actor_id: uuid.UUID,
    actor_role: MembershipRole,
) -> None:
    await RequirementRepository(session, tenant_id=tenant_id, project_id=project_id).get_by_id(requirement_id)
    comment = await _load_own_comment(session, requirement_id=requirement_id, comment_id=comment_id)
    _assert_can_moderate(comment, actor_id=actor_id, actor_role=actor_role)

    await AuditEventRepository(session, tenant_id=tenant_id).record(
        event_type=AuditEventType.REQUIREMENT_COMMENT_DELETED,
        actor_id=actor_id,
        target_type="requirement",
        target_id=requirement_id,
        metadata={"comment_id": str(comment.id)},
    )
    await RequirementCommentRepository(session).delete(comment)
    await session.commit()
