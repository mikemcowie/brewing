from collections.abc import Sequence
from dataclasses import make_dataclass
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from runtime_generic import runtime_generic
from sqlalchemy.ext.asyncio import AsyncSession

from cauldron.auth.models import User
from cauldron.auth.users import user
from cauldron.db import session
from cauldron.exceptions import Unauthorized
from cauldron.http import Depends, Path, status
from cauldron.http.viewset import AbstractViewSet, APIPathConstant, APIPathParam
from cauldron.resources.models import AccessLevel, Resource, ResourceAccessItem
from cauldron.resources.repo import (
    CrudRepository,
)

if TYPE_CHECKING:
    from pydantic import BaseModel

    CreateResource = BaseModel
    UpdateResource = BaseModel
    ResourceRead = BaseModel
    ResourceSummary = BaseModel


@runtime_generic
class ModelViewSet[ModelT: Resource](AbstractViewSet):
    model: type[ModelT]

    def get_base_path(self) -> Sequence[APIPathConstant | APIPathParam]:
        return [APIPathConstant(self.model.plural_name)]

    def get_router_tags(self) -> list[str | Enum]:
        return [self.model.plural_name]

    def get_router_dependencies(self) -> Sequence[Any]:
        return [Depends(user)]

    def setup_endpoints(self):  # noqa: C901
        path_param_name = f"{self.model.singular_name}_id"
        if not TYPE_CHECKING:
            # Annotions that are read by fastapi at runtime
            # However pyright doesn't see them as valid
            # So alternatives are defined in import block for type checker to see.
            CreateResource = self.model.schemas().create  # noqa: N806
            UpdateResource = self.model.schemas().update  # noqa: N806
            ResourceRead = self.model.schemas().read  # noqa: N806
            ResourceSummary = self.model.schemas().summary  # noqa: N806

        class Endpoints:
            RESOURCES = f"/{self.model.plural_name}/"
            RESOURCES_ONE = "{}{}".format(RESOURCES, f"{{{path_param_name}}}")
            RESOURCES_ONE_ACCESS = f"{RESOURCES_ONE}/access"
            RESOURCES_ONE_ACCESS_ONE = f"{RESOURCES_ONE}/access/{{user_id}}"

        InstancePathParams = make_dataclass(  # noqa: N806
            "InstancePathParams", [(path_param_name, Annotated[UUID, Path()])]
        )

        def resource_id(param: Annotated[InstancePathParams, Depends()]):  # type: ignore
            return getattr(param, path_param_name)

        async def repo(
            db_session: Annotated[AsyncSession, Depends(session.db_session)],
            user: Annotated[User, Depends(user)],
        ):
            return CrudRepository[self.model](db_session, user)

        async def access_level(
            repo: Annotated[CrudRepository[ModelT], Depends(repo)],
            resource_id: Annotated[UUID, Depends(resource_id)],
        ) -> AccessLevel:
            return (
                await repo.get_access_one(resource_id=resource_id, user_id=repo.user.id)
            ).access

        async def access_org_owner(
            access_level: Annotated[AccessLevel, Depends(access_level)],
        ):
            if access_level.is_owner():
                return True
            raise Unauthorized(detail="access denied")

        async def access_org_contributor(
            access_level: Annotated[AccessLevel, Depends(access_level)],
        ):
            if access_level.is_contributor():
                return True
            raise Unauthorized(detail="access denied")

        async def access_org_reader(
            access_level: Annotated[AccessLevel, Depends(access_level)],
        ):
            if access_level.is_reader():
                return True
            raise Unauthorized(detail="access denied")

        @self.router.post(
            Endpoints.RESOURCES,
            status_code=status.HTTP_201_CREATED,
            response_model=ResourceRead,
        )
        async def create_resource(
            create: CreateResource,
            repo: Annotated[CrudRepository[ModelT], Depends(repo)],
        ) -> ResourceRead:
            return await repo.create(create)

        @self.router.get(Endpoints.RESOURCES, response_model=list[ResourceSummary])
        async def list_resource(
            repo: Annotated[CrudRepository[ModelT], Depends(repo)],
        ) -> Sequence[ResourceSummary]:
            return await repo.list_resources()

        @self.router.get(
            Endpoints.RESOURCES_ONE,
            response_model=ResourceRead,
            dependencies=[Depends(access_org_reader)],
        )
        async def read_resource(
            resource_id: Annotated[UUID, Depends(resource_id)],
            repo: Annotated[CrudRepository[ModelT], Depends(repo)],
        ) -> ResourceRead:
            return ResourceRead.model_validate(
                await repo.get(resource_id), from_attributes=True
            )

        @self.router.put(
            Endpoints.RESOURCES_ONE,
            response_model=ResourceRead,
            dependencies=[Depends(access_org_contributor)],
        )
        async def update_resource(
            resource_id: Annotated[UUID, Depends(resource_id)],
            update: UpdateResource,
            repo: Annotated[CrudRepository[ModelT], Depends(repo)],
        ) -> ResourceRead:
            return await repo.update(resource_id, update)

        @self.router.delete(
            Endpoints.RESOURCES_ONE,
            status_code=status.HTTP_204_NO_CONTENT,
            dependencies=[Depends(access_org_owner)],
        )
        async def delete_resource(
            resource_id: Annotated[UUID, Depends(resource_id)],
            repo: Annotated[CrudRepository[ModelT], Depends(repo)],
        ) -> None:
            await repo.delete(resource_id)

        @self.router.get(
            Endpoints.RESOURCES_ONE_ACCESS,
            response_model=list[ResourceAccessItem],
            dependencies=[Depends(access_org_contributor)],
        )
        async def get_access(
            resource_id: Annotated[UUID, Depends(resource_id)],
            repo: Annotated[CrudRepository[ModelT], Depends(repo)],
        ) -> list[ResourceAccessItem]:
            return await repo.get_access(resource_id)

        @self.router.get(
            Endpoints.RESOURCES_ONE_ACCESS_ONE,
            response_model=ResourceAccessItem,
            dependencies=[Depends(access_org_contributor)],
        )
        async def get_access_one(
            resource_id: Annotated[UUID, Depends(resource_id)],
            user_id: UUID,
            repo: Annotated[CrudRepository[ModelT], Depends(repo)],
        ) -> ResourceAccessItem:
            return await repo.get_access_one(resource_id, user_id)

        @self.router.post(
            Endpoints.RESOURCES_ONE_ACCESS,
            response_model=list[ResourceAccessItem],
            dependencies=[Depends(access_org_owner)],
        )
        async def set_access(
            resource_id: Annotated[UUID, Depends(resource_id)],
            access: ResourceAccessItem | list[ResourceAccessItem],
            repo: Annotated[CrudRepository[ModelT], Depends(repo)],
        ) -> list[ResourceAccessItem]:
            if isinstance(access, ResourceAccessItem):
                access = [access]
            return await repo.set_access(resource_id, access)
