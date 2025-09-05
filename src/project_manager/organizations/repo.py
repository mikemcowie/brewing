from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from project_manager.exceptions import Forbidden, NotFound
from project_manager.organizations.models import Organization
from project_manager.resources.models import AccessLevel, ResourceAccess
from project_manager.users.models import User

if TYPE_CHECKING:  # Type checker type hints (just that its a model)
    from pydantic import BaseModel

    OrganizationRead = BaseModel
    OrganizationSummary = BaseModel
    CreateOrganization = BaseModel
    UpdateOrganization = BaseModel
else:  # At runtime we derive these from the sqlalchemy mapped class
    OrganizationRead = Organization.schemas().read
    OrganizationSummary = Organization.schemas().summary
    CreateOrganization = Organization.schemas().create
    UpdateOrganization = Organization.schemas().update


class OrganizationRepository:
    def __init__(self, session: AsyncSession, user: User):
        self.session = session
        self.user = user
        self.base_query = (
            select(Organization)
            .where(Organization.deleted == None)  # noqa: E711
            .join(ResourceAccess)
        )

    async def create(self, new_organization: CreateOrganization):
        organization = Organization(**new_organization.model_dump())
        access = ResourceAccess(
            resource=organization, user=self.user, access=AccessLevel.owner
        )
        self.session.add_all((organization, access))
        await self.session.commit()
        return OrganizationRead.model_validate(organization, from_attributes=True)

    async def list(self):
        return [
            OrganizationSummary.model_validate(org, from_attributes=True)
            for org in (await self.session.execute(self.base_query)).scalars()
        ]

    async def get(
        self, organization_id: UUID, access_level: AccessLevel = AccessLevel.reader
    ):
        query = self.base_query.where(Organization.id == organization_id).where(
            ResourceAccess.user_id == self.user.id
        )
        if org := (await self.session.execute(query)).scalar_one_or_none():
            if access_level == AccessLevel.reader:
                return org
            if access_level == AccessLevel.contributor:
                query = query.where(
                    ResourceAccess.access.in_(
                        (AccessLevel.owner, AccessLevel.contributor)
                    )
                )
            if access_level == AccessLevel.owner:
                query = query.where(ResourceAccess.access == AccessLevel.owner)
            second_org_result = (await self.session.execute(query)).scalar_one_or_none()
            if second_org_result:
                return second_org_result
            raise Forbidden()

        raise NotFound(detail=f"{organization_id=!s} not found.")

    async def update(
        self,
        organization_id: UUID,
        update: UpdateOrganization,
    ) -> OrganizationRead:
        organization = await self.get(
            organization_id, access_level=AccessLevel.contributor
        )
        for k, v in update.model_dump().items():
            setattr(organization, k, v)
        await self.session.commit()
        return OrganizationRead.model_validate(organization, from_attributes=True)

    async def delete(self, organization_id: UUID):
        org = await self.get(organization_id)
        org.deleted = datetime.now(UTC)
        await self.session.commit()
