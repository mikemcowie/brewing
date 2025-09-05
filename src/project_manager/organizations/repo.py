from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from project_manager.exceptions import Forbidden, NotFound
from project_manager.organizations.models import Organization
from project_manager.resources.models import (
    AccessLevel,
    Resource,
    ResourceAccess,
    ResourceAccessItem,
)
from project_manager.users.models import User

if TYPE_CHECKING:  # Type checker type hints (just that its a model)
    from pydantic import BaseModel

    ResourceRead = BaseModel
    ResourceSummary = BaseModel
    CreateResource = BaseModel
    UpdateResource = BaseModel
else:  # At runtime we derive these from the sqlalchemy mapped class
    ResourceRead = Organization.schemas().read
    ResourceSummary = Organization.schemas().summary
    CreateResource = Organization.schemas().create
    UpdateResource = Organization.schemas().update


class OrganizationRepository:
    db_model: type[Resource] = Organization

    def __init__(self, session: AsyncSession, user: User):
        self.session = session
        self.user = user
        self.base_query = (
            select(self.db_model)
            .where(self.db_model.deleted == None)  # noqa: E711
            .join(ResourceAccess)
        )

    async def create(self, new_resource: CreateResource):
        resource = self.db_model(**new_resource.model_dump())
        self.session.add(resource)
        await self.session.flush()
        access = ResourceAccess(
            resource_id=resource.id, user_id=self.user.id, access=AccessLevel.owner
        )
        self.session.add_all((resource, access))
        await self.session.commit()
        return ResourceRead.model_validate(resource, from_attributes=True)

    async def list_resources(self):
        return [
            ResourceSummary.model_validate(resource, from_attributes=True)
            for resource in (await self.session.execute(self.base_query)).scalars()
        ]

    async def get(
        self, resource_id: UUID, access_level: AccessLevel = AccessLevel.reader
    ):
        query = self.base_query.where(self.db_model.id == resource_id).where(
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

        raise NotFound(detail=f"{resource_id=!s} not found.")

    async def update(
        self,
        organization_id: UUID,
        update: UpdateResource,
    ) -> ResourceRead:
        organization = await self.get(
            organization_id, access_level=AccessLevel.contributor
        )
        for k, v in update.model_dump().items():
            setattr(organization, k, v)
        await self.session.commit()
        return ResourceRead.model_validate(organization, from_attributes=True)

    async def delete(self, organization_id: UUID):
        org = await self.get(organization_id)
        org.deleted = datetime.now(UTC)
        await self.session.commit()

    def _base_access_query(
        self, organization_id: UUID | None = None, user_id: UUID | None = None
    ):
        q = select(ResourceAccess)
        if organization_id:
            q = q.where(ResourceAccess.resource_id == organization_id)
        if user_id:
            q = q.where(ResourceAccess.user_id == user_id)
        return q

    async def get_access(self, organization_id: UUID):
        return [
            ResourceAccessItem.model_validate(a, from_attributes=True)
            for a in (
                await self.session.execute(
                    self._base_access_query(organization_id=organization_id)
                )
            )
            .scalars()
            .all()
        ]

    async def get_access_one(self, organization_id: UUID, user_id: UUID):
        resource = (
            (
                await self.session.execute(
                    self._base_access_query(
                        organization_id=organization_id, user_id=user_id
                    )
                )
            )
            .scalars()
            .one_or_none()
        )
        if not resource:
            raise NotFound(f"no access found for {organization_id=}, {user_id=}")
        return ResourceAccessItem.model_validate(
            resource,
            from_attributes=True,
        )

    async def set_access(self, organization_id: UUID, access: list[ResourceAccessItem]):
        current_access = (
            (
                await self.session.execute(
                    self._base_access_query(organization_id=organization_id).where(
                        ResourceAccess.user_id.in_([a.user_id for a in access])
                    )
                )
            )
            .scalars()
            .all()
        )
        users_to_db_item = {a.user_id: a for a in current_access}
        for access_item in access:
            if access_item.user_id in users_to_db_item:
                users_to_db_item[access_item.user_id].access = access_item.access
            else:
                self.session.add(
                    ResourceAccess(
                        resource_id=organization_id,
                        access=access_item.access,
                        user_id=access_item.user_id,
                    )
                )
        await self.session.commit()
        return await self.get_access(organization_id=organization_id)
