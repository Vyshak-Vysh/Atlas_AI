"""Repositories for tenants, users, memberships, projects, and phases.

`tenants` and `users` sit above the tenant/project scoping model (a tenant
scopes itself; a user's tenant membership is a join, not a column) so their
repositories don't inherit TenantScopedRepository/ProjectScopedRepository —
they implement their own narrow, explicit query surface instead.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_db.exceptions import NotFoundError
from atlasai_db.models.tenancy import Phase, Project, ProjectMember, Space, Sprint, Tenant, TenantMember, User
from atlasai_db.repositories.base import ProjectScopedRepository, TenantScopedRepository


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, tenant_id: uuid.UUID) -> Tenant:
        row = await self.session.get(Tenant, tenant_id)
        if row is None:
            raise NotFoundError("Tenant", tenant_id)
        return row

    async def get_by_slug(self, slug: str) -> Tenant | None:
        result = await self.session.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def create(self, *, name: str, slug: str) -> Tenant:
        tenant = Tenant(name=name, slug=slug)
        self.session.add(tenant)
        await self.session.flush()
        return tenant


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        row = await self.session.get(User, user_id)
        if row is None:
            raise NotFoundError("User", user_id)
        return row

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, *, email: str, display_name: str, auth_subject: str) -> User:
        user = User(email=email, display_name=display_name, auth_subject=auth_subject)
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_display_name(self, user: User, display_name: str) -> User:
        user.display_name = display_name
        await self.session.flush()
        return user


class MembershipRepository:
    """Tenant- and project-membership lookups used by the authorization
    layer (packages/security) to resolve a user's role before any
    tenant/project-scoped repository is constructed."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_tenant_role(self, *, tenant_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
        result = await self.session.execute(
            select(TenantMember.role).where(
                TenantMember.tenant_id == tenant_id, TenantMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_project_role(self, *, project_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
        result = await self.session.execute(
            select(ProjectMember.role).where(
                ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def add_tenant_member(self, *, tenant_id: uuid.UUID, user_id: uuid.UUID, role: str) -> TenantMember:
        member = TenantMember(tenant_id=tenant_id, user_id=user_id, role=role)
        self.session.add(member)
        await self.session.flush()
        return member

    async def add_project_member(self, *, project_id: uuid.UUID, user_id: uuid.UUID, role: str) -> ProjectMember:
        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        self.session.add(member)
        await self.session.flush()
        return member

    async def list_tenant_memberships_for_user(self, user_id: uuid.UUID) -> list[tuple[TenantMember, Tenant]]:
        result = await self.session.execute(
            select(TenantMember, Tenant)
            .join(Tenant, Tenant.id == TenantMember.tenant_id)
            .where(TenantMember.user_id == user_id)
            .order_by(Tenant.name)
        )
        return [(row.TenantMember, row.Tenant) for row in result]

    async def list_project_ids_for_user(self, *, tenant_id: uuid.UUID, user_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self.session.execute(
            select(ProjectMember.project_id)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(Project.tenant_id == tenant_id, ProjectMember.user_id == user_id)
        )
        return list(result.scalars().all())

    async def count_project_members(self, project_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(ProjectMember).where(ProjectMember.project_id == project_id)
        )
        return int(result.scalar_one())

    async def list_tenant_members(self, tenant_id: uuid.UUID) -> list[tuple[TenantMember, User]]:
        result = await self.session.execute(
            select(TenantMember, User)
            .join(User, User.id == TenantMember.user_id)
            .where(TenantMember.tenant_id == tenant_id)
            .order_by(User.display_name)
        )
        return [(row.TenantMember, row.User) for row in result]

    async def list_project_members(self, project_id: uuid.UUID) -> list[tuple[ProjectMember, User]]:
        result = await self.session.execute(
            select(ProjectMember, User)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(User.display_name)
        )
        return [(row.ProjectMember, row.User) for row in result]

    async def update_tenant_member_role(
        self, *, tenant_id: uuid.UUID, user_id: uuid.UUID, role: str
    ) -> TenantMember | None:
        result = await self.session.execute(
            select(TenantMember).where(TenantMember.tenant_id == tenant_id, TenantMember.user_id == user_id)
        )
        member = result.scalar_one_or_none()
        if member is None:
            return None
        member.role = role
        await self.session.flush()
        return member

    async def remove_tenant_member(self, *, tenant_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(TenantMember).where(TenantMember.tenant_id == tenant_id, TenantMember.user_id == user_id)
        )
        member = result.scalar_one_or_none()
        if member is None:
            return False
        await self.session.delete(member)
        await self.session.flush()
        return True

    async def update_project_member_role(
        self, *, project_id: uuid.UUID, user_id: uuid.UUID, role: str
    ) -> ProjectMember | None:
        result = await self.session.execute(
            select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        )
        member = result.scalar_one_or_none()
        if member is None:
            return None
        member.role = role
        await self.session.flush()
        return member

    async def remove_project_member(self, *, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        )
        member = result.scalar_one_or_none()
        if member is None:
            return False
        await self.session.delete(member)
        await self.session.flush()
        return True


async def resolve_tenant_id_for_project(session: AsyncSession, project_id: uuid.UUID) -> uuid.UUID | None:
    """The one intentionally tenant-unscoped lookup in this package: given
    only a project_id (e.g. from a URL path), find which tenant owns it so
    a properly-scoped repository can then be constructed. This does not
    itself grant access — every caller must still check project/tenant
    membership via MembershipRepository before returning any project data."""
    result = await session.execute(select(Project.tenant_id).where(Project.id == project_id))
    return result.scalar_one_or_none()


class ProjectRepository(TenantScopedRepository[Project]):
    model = Project

    async def get_by_code(self, code: str) -> Project | None:
        query = self._scoped_query().where(Project.code == code)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        name: str,
        client_name: str | None = None,
        code: str | None = None,
        timezone: str = "UTC",
        space_id: uuid.UUID | None = None,
    ) -> Project:
        project = Project(
            tenant_id=self.tenant_id,
            name=name,
            client_name=client_name,
            code=code,
            timezone=timezone,
            space_id=space_id,
        )
        return await self.add(project)

    async def update(
        self,
        project: Project,
        *,
        name: str | None = None,
        client_name: str | None = None,
        status: str | None = None,
        space_id: uuid.UUID | None = None,
    ) -> Project:
        """`None` means "leave unchanged" for every field here — there is no
        supported way to clear `client_name`/`space_id` back to null via this
        method, matching the other partial-update endpoints in this
        codebase."""
        if name is not None:
            project.name = name
        if client_name is not None:
            project.client_name = client_name
        if status is not None:
            project.status = status
        if space_id is not None:
            project.space_id = space_id
        await self.session.flush()
        return project

    async def list_by_space(self, space_id: uuid.UUID) -> list[Project]:
        query = self._scoped_query().where(Project.space_id == space_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class PhaseRepository(ProjectScopedRepository[Phase]):
    model = Phase

    async def create(
        self, *, name: str, phase_number: int, start_date: date | None = None, end_date: date | None = None
    ) -> Phase:
        phase = Phase(
            project_id=self.project_id,
            name=name,
            phase_number=phase_number,
            start_date=start_date,
            end_date=end_date,
        )
        return await self.add(phase)


class SpaceRepository(TenantScopedRepository[Space]):
    model = Space

    async def get_by_name(self, name: str) -> Space | None:
        query = self._scoped_query().where(Space.name == name)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        name: str,
        description: str | None = None,
        color: str | None = None,
    ) -> Space:
        space = Space(tenant_id=self.tenant_id, name=name, description=description, color=color)
        return await self.add(space)

    async def update(
        self,
        space: Space,
        *,
        name: str | None = None,
        description: str | None = None,
        color: str | None = None,
        status: str | None = None,
    ) -> Space:
        if name is not None:
            space.name = name
        if description is not None:
            space.description = description
        if color is not None:
            space.color = color
        if status is not None:
            space.status = status
        await self.session.flush()
        return space

    async def count_projects(self, space_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Project).where(Project.space_id == space_id)
        )
        return int(result.scalar_one())


class SprintRepository(ProjectScopedRepository[Sprint]):
    model = Sprint

    async def get_by_number(self, sprint_number: int) -> Sprint | None:
        query = self._scoped_query().where(Sprint.sprint_number == sprint_number)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        name: str,
        sprint_number: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Sprint:
        sprint = Sprint(
            project_id=self.project_id,
            name=name,
            sprint_number=sprint_number,
            start_date=start_date,
            end_date=end_date,
        )
        return await self.add(sprint)

    async def update(
        self,
        sprint: Sprint,
        *,
        name: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> Sprint:
        if name is not None:
            sprint.name = name
        if start_date is not None:
            sprint.start_date = start_date
        if end_date is not None:
            sprint.end_date = end_date
        if status is not None:
            sprint.status = status
        await self.session.flush()
        return sprint
