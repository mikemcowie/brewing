from dataclasses import make_dataclass
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from cauldron import db
from cauldron.exceptions import Unauthorized
from cauldron.resources.models import AccessLevel, Resource, ResourceAccessItem
from cauldron.resources.repo import (
    CrudRepository,
)
from cauldron.users import User, user

if TYPE_CHECKING:
    CreateResource = BaseModel
    UpdateResource = BaseModel
    ResourceRead = BaseModel
    ResourceSummary = BaseModel


def model_crud_router[ModelT: Resource](model_type: type[ModelT]):  # noqa: C901
    router = APIRouter(tags=[model_type.plural_name], dependencies=[Depends(user)])
    path_param_name = f"{model_type.singular_name}_id"
    if not TYPE_CHECKING:
        # Annotions that are read by fastapi at runtime
        # However pyright doesn't see them as valid
        # So alternatives are defined in import block for type checker to see.
        CreateResource = model_type.schemas().create  # noqa: N806
        UpdateResource = model_type.schemas().update  # noqa: N806
        ResourceRead = model_type.schemas().read  # noqa: N806
        ResourceSummary = model_type.schemas().summary  # noqa: N806

    class Endpoints:
        RESOURCES = f"/{model_type.plural_name}/"
        RESOURCES_ONE = "{}{}".format(RESOURCES, f"{{{path_param_name}}}")
        RESOURCES_ONE_ACCESS = f"{RESOURCES_ONE}/access"
        RESOURCES_ONE_ACCESS_ONE = f"{RESOURCES_ONE}/access/{{user_id}}"

    InstancePathParams = make_dataclass(  # noqa: N806
        "InstancePathParams", [(path_param_name, Annotated[UUID, Path()])]
    )

    def resource_id(param: Annotated[InstancePathParams, Depends()]):  # type: ignore
        return getattr(param, path_param_name)

    async def repo(
        db_session: Annotated[AsyncSession, Depends(db.db_session)],
        user: Annotated[User, Depends(user)],
    ):
        return CrudRepository[model_type](db_session, user)

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

    @router.post(
        Endpoints.RESOURCES,
        status_code=status.HTTP_201_CREATED,
        response_model=ResourceRead,
    )
    async def create_resource(
        create: CreateResource, repo: Annotated[CrudRepository[ModelT], Depends(repo)]
    ) -> ResourceRead:
        return await repo.create(create)

    @router.get(Endpoints.RESOURCES, response_model=list[ResourceSummary])
    async def list_resource(
        repo: Annotated[CrudRepository[ModelT], Depends(repo)],
    ) -> list[ResourceSummary]:
        return await repo.list_resources()

    @router.get(
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

    @router.put(
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

    @router.delete(
        Endpoints.RESOURCES_ONE,
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[Depends(access_org_owner)],
    )
    async def delete_resource(
        resource_id: Annotated[UUID, Depends(resource_id)],
        repo: Annotated[CrudRepository[ModelT], Depends(repo)],
    ) -> None:
        await repo.delete(resource_id)

    @router.get(
        Endpoints.RESOURCES_ONE_ACCESS,
        response_model=list[ResourceAccessItem],
        dependencies=[Depends(access_org_contributor)],
    )
    async def get_access(
        resource_id: Annotated[UUID, Depends(resource_id)],
        repo: Annotated[CrudRepository[ModelT], Depends(repo)],
    ) -> list[ResourceAccessItem]:
        return await repo.get_access(resource_id)

    @router.get(
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

    @router.post(
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

    return router
