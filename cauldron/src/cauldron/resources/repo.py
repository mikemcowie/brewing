from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cauldron.exceptions import Forbidden, NotFound
from cauldron.resources.models import (
    AccessLevel,
    Resource,
    ResourceAccess,
    ResourceAccessItem,
)
from cauldron.users import User

if TYPE_CHECKING:  # Type checker type hints (just that its a model)
    from pydantic import BaseModel

    ResourceRead = BaseModel
    ResourceSummary = BaseModel
    CreateResource = BaseModel
    UpdateResource = BaseModel


class CrudRepository[ModelT: Resource]:
    db_model: type[ModelT]

    def __class_getitem__(cls, resource_type: type[Resource]):
        return type(cls.__name__, (cls,), {"db_model": resource_type})

    def __init__(self, session: AsyncSession, user: User):
        if not getattr(self, "db_model", None):
            raise NotImplementedError(
                "Cannot instantiate unspecialized CrudRepository."
                "Create a subclass or attach a particular model type via "
                f"{self.__class__.__name__}[ResourceModelType]"
            )
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
        return self.db_model.schemas().read.model_validate(
            resource, from_attributes=True
        )

    async def list_resources(self):
        return [
            self.db_model.schemas().read.model_validate(resource, from_attributes=True)
            for resource in (await self.session.execute(self.base_query)).scalars()
        ]

    async def get(
        self, resource_id: UUID, access_level: AccessLevel = AccessLevel.reader
    ):
        query = self.base_query.where(self.db_model.id == resource_id).where(
            ResourceAccess.user_id == self.user.id
        )
        if resource := (await self.session.execute(query)).scalar_one_or_none():
            if access_level == AccessLevel.reader:
                return resource
            if access_level == AccessLevel.contributor:
                query = query.where(
                    ResourceAccess.access.in_(
                        (AccessLevel.owner, AccessLevel.contributor)
                    )
                )
            if access_level == AccessLevel.owner:
                query = query.where(ResourceAccess.access == AccessLevel.owner)
            second_resource = (await self.session.execute(query)).scalar_one_or_none()
            if second_resource:
                return second_resource
            raise Forbidden()

        raise NotFound(detail=f"{resource_id=!s} not found.")

    async def update(
        self,
        resource_id: UUID,
        update: UpdateResource,
    ) -> ResourceRead:
        resource = await self.get(resource_id, access_level=AccessLevel.contributor)
        for k, v in update.model_dump().items():
            setattr(resource, k, v)
        await self.session.commit()
        return self.db_model.schemas().read.model_validate(
            resource, from_attributes=True
        )

    async def delete(self, resource_id: UUID):
        resource = await self.get(resource_id)
        resource.deleted = datetime.now(UTC)
        await self.session.commit()

    def _base_access_query(
        self, resource_id: UUID | None = None, user_id: UUID | None = None
    ):
        q = select(ResourceAccess)
        if resource_id:
            q = q.where(ResourceAccess.resource_id == resource_id)
        if user_id:
            q = q.where(ResourceAccess.user_id == user_id)
        return q

    async def get_access(self, resource_id: UUID):
        return [
            ResourceAccessItem.model_validate(a, from_attributes=True)
            for a in (
                await self.session.execute(
                    self._base_access_query(resource_id=resource_id)
                )
            )
            .scalars()
            .all()
        ]

    async def get_access_one(self, resource_id: UUID, user_id: UUID):
        resource = (
            (
                await self.session.execute(
                    self._base_access_query(resource_id=resource_id, user_id=user_id)
                )
            )
            .scalars()
            .one_or_none()
        )
        if not resource:
            raise NotFound(f"no access found for {resource_id=}, {user_id=}")
        return ResourceAccessItem.model_validate(
            resource,
            from_attributes=True,
        )

    async def set_access(self, resource_id: UUID, access: list[ResourceAccessItem]):
        current_access = (
            (
                await self.session.execute(
                    self._base_access_query(resource_id=resource_id).where(
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
                        resource_id=resource_id,
                        access=access_item.access,
                        user_id=access_item.user_id,
                    )
                )
        await self.session.commit()
        return await self.get_access(resource_id=resource_id)
