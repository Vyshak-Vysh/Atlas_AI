"""Unit tests for packages/security/rbac.py (BD_v2.md §4 roles table)."""

from __future__ import annotations

from atlasai_domain.enums import MembershipRole
from atlasai_security.rbac import Permission, can_view_internal_evidence, role_has_permission


def test_client_viewer_can_never_view_internal_evidence() -> None:
    """BR-016: client-facing content must never expose internal-only
    evidence — this is the one invariant that must never regress."""
    assert can_view_internal_evidence(MembershipRole.CLIENT_VIEWER) is False


def test_client_viewer_can_view_the_project_but_nothing_administrative() -> None:
    assert role_has_permission(MembershipRole.CLIENT_VIEWER, Permission.VIEW_PROJECT)
    assert not role_has_permission(MembershipRole.CLIENT_VIEWER, Permission.APPROVE_ACTION)
    assert not role_has_permission(MembershipRole.CLIENT_VIEWER, Permission.MANAGE_CONNECTORS)


def test_ai_engineer_admin_has_full_access() -> None:
    for permission in Permission:
        assert role_has_permission(MembershipRole.AI_ENGINEER_ADMIN, permission)


def test_worker_cannot_approve_actions_or_run_agent() -> None:
    """TD_v2.md/BD_v2.md: workers sync/parse/embed/evaluate but have no
    independent external-write or investigation authority."""
    assert not role_has_permission(MembershipRole.WORKER, Permission.APPROVE_ACTION)
    assert not role_has_permission(MembershipRole.WORKER, Permission.RUN_AGENT)
    assert role_has_permission(MembershipRole.WORKER, Permission.SYNC_SOURCE)


def test_project_manager_can_approve_actions() -> None:
    assert role_has_permission(MembershipRole.PROJECT_MANAGER, Permission.APPROVE_ACTION)
    assert not role_has_permission(MembershipRole.PROJECT_MANAGER, Permission.MANAGE_CONNECTORS)


_TASK_PERMISSIONS = (
    Permission.CREATE_TASK,
    Permission.EDIT_TASK,
    Permission.DELETE_TASK,
    Permission.ASSIGN_TASK,
    Permission.COMMENT_ON_TASK,
)


def test_client_viewer_cannot_write_tasks() -> None:
    """CLIENT_VIEWER is view-only across the whole task board — it must
    never gain create/edit/delete/assign/comment rights on a task."""
    for permission in _TASK_PERMISSIONS:
        assert not role_has_permission(MembershipRole.CLIENT_VIEWER, permission)


def test_every_non_client_viewer_role_can_fully_manage_tasks() -> None:
    """Every other project role gets full task read/write, ClickUp-style."""
    for role in MembershipRole:
        if role is MembershipRole.CLIENT_VIEWER:
            continue
        for permission in _TASK_PERMISSIONS:
            assert role_has_permission(role, permission), f"{role} should have {permission}"
