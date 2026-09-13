"""Role-based capability checks (BD_v2.md §4 roles table).

This module answers "can this role do X" as a pure function of
`MembershipRole` — it does not know about requests, sessions, or the
database. The API layer's authorization dependency resolves a user's role
via `atlasai_db.repositories.tenancy.MembershipRepository` and then calls
into here; the negative-authorization test suite exercises this module
directly as well as through the API.
"""

from __future__ import annotations

from enum import StrEnum

from atlasai_domain.enums import MembershipRole


class Permission(StrEnum):
    VIEW_PROJECT = "VIEW_PROJECT"
    VIEW_INTERNAL_EVIDENCE = "VIEW_INTERNAL_EVIDENCE"
    UPLOAD_DOCUMENT = "UPLOAD_DOCUMENT"
    CONNECT_SOURCE = "CONNECT_SOURCE"
    SYNC_SOURCE = "SYNC_SOURCE"
    RUN_AGENT = "RUN_AGENT"
    APPROVE_ACTION = "APPROVE_ACTION"
    MANAGE_CONNECTORS = "MANAGE_CONNECTORS"
    MANAGE_POLICIES = "MANAGE_POLICIES"
    VIEW_AUDIT_LOG = "VIEW_AUDIT_LOG"
    MANAGE_PROJECT_MEMBERS = "MANAGE_PROJECT_MEMBERS"


_ROLE_PERMISSIONS: dict[MembershipRole, frozenset[Permission]] = {
    MembershipRole.PROJECT_MANAGER: frozenset(
        {
            Permission.VIEW_PROJECT,
            Permission.VIEW_INTERNAL_EVIDENCE,
            Permission.UPLOAD_DOCUMENT,
            Permission.SYNC_SOURCE,
            Permission.RUN_AGENT,
            Permission.APPROVE_ACTION,
            Permission.VIEW_AUDIT_LOG,
            Permission.MANAGE_PROJECT_MEMBERS,
        }
    ),
    MembershipRole.AI_ENGINEER_ADMIN: frozenset(set(Permission)),  # full access, incl. elevated/destructive ops
    MembershipRole.CEO_SALES: frozenset(
        {
            Permission.VIEW_PROJECT,
            Permission.RUN_AGENT,
            Permission.VIEW_AUDIT_LOG,
        }
    ),
    MembershipRole.DELIVERY_TEAM: frozenset(
        {
            Permission.VIEW_PROJECT,
            Permission.VIEW_INTERNAL_EVIDENCE,
            Permission.UPLOAD_DOCUMENT,
            Permission.RUN_AGENT,
        }
    ),
    MembershipRole.CLIENT_VIEWER: frozenset({Permission.VIEW_PROJECT}),  # never VIEW_INTERNAL_EVIDENCE — BR-016
    MembershipRole.WORKER: frozenset(
        {
            Permission.SYNC_SOURCE,
            Permission.UPLOAD_DOCUMENT,
        }
    ),
}


def role_has_permission(role: MembershipRole, permission: Permission) -> bool:
    return permission in _ROLE_PERMISSIONS.get(role, frozenset())


def can_view_internal_evidence(role: MembershipRole) -> bool:
    """BR-016: client-facing content must never expose internal-only
    evidence — CLIENT_VIEWER is the one role this must always be false for."""
    return role_has_permission(role, Permission.VIEW_INTERNAL_EVIDENCE)
