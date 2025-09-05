from collections.abc import Sequence
from dataclasses import make_dataclass
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from cauldronlib.generic import runtime_generic
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from cauldron.auth.models import User
from cauldron.auth.users import user
from cauldron.db import session
from cauldron.exceptions import Unauthorized
from cauldron.http import Depends, Path, status
from cauldron.http.viewset import (
    AbstractViewSet,
    APIPathConstant,
    Endpoint,
    EndpointParameters,
    const,
)
from cauldron.http.viewset.base import PathParameterPlaceholder
from cauldron.resources.models import AccessLevel, Resource, ResourceAccessItem
from cauldron.resources.repo import (
    CrudRepository,
)

if TYPE_CHECKING:
    CreateResource = BaseModel
    UpdateResource = BaseModel
    ResourceRead = BaseModel
    ResourceSummary = BaseModel


class _CreateResource(BaseModel):
    """Placeholder for the create resource schema."""


class _UpdateResource(BaseModel):
    """Placeholder for the update resource schema."""


class _ResourceRead(BaseModel):
    """Placeholder for the resource read schema."""


class _ResourceList(BaseModel):
    """Placeholder for the resource read schema."""


@runtime_generic
class ModelViewSet[ModelT: Resource](AbstractViewSet):
    model: type[ModelT]

    def get_base_path(self) -> Sequence[str]:
        return [APIPathConstant(self.model.plural_name)]

    def get_router_tags(self) -> list[str | Enum]:
        return [self.model.plural_name]

    def get_dependencies(self) -> Sequence[Any]:
        return [Depends(user)]

    def get_path_param_name(self):
        return f"{self.model.singular_name}_id"

    def get_path_params_class(self):
        return make_dataclass(
            "InstancePathParams",
            [(self.get_path_param_name(), Annotated[UUID, Path()])],
        )

    def resource_id(self, param: Annotated[PathParameterPlaceholder, Depends()]):  # type: ignore
        return getattr(param, self.get_path_param_name())

    async def repo(
        self,
        db_session: Annotated[AsyncSession, Depends(session.db_session)],
        user: Annotated[User, Depends(user)],
    ):
        return CrudRepository[self.model](db_session, user)

    async def access_level(
        self,
        repo: Annotated[CrudRepository[ModelT], Depends(repo)],
        resource_id: Annotated[UUID, Depends(resource_id)],
    ) -> AccessLevel:
        return (
            await repo.get_access_one(resource_id=resource_id, user_id=repo.user.id)
        ).access

    async def access_org_owner(
        self,
        access_level: Annotated[AccessLevel, Depends(access_level)],
    ):
        if access_level.is_owner():
            return True
        raise Unauthorized(detail="access denied")

    async def access_org_contributor(
        self,
        access_level: Annotated[AccessLevel, Depends(access_level)],
    ):
        if access_level.is_contributor():
            return True
        raise Unauthorized(detail="access denied")

    async def access_org_reader(
        self,
        access_level: Annotated[AccessLevel, Depends(access_level)],
    ):
        if access_level.is_reader():
            return True
        raise Unauthorized(detail="access denied")

    collection = Endpoint(trailing_slash=True)
    single = collection.path_parameter()
    access = single.action("access")
    access_single = access.path_parameter("user_id")

    @collection.POST(
        status_code=status.HTTP_201_CREATED,
        response_model=_ResourceRead,
    )
    async def create_resource(
        self,
        create: _CreateResource,
        repo: Annotated[CrudRepository[ModelT], Depends(repo)],
    ):
        return await repo.create(create)

    @collection.GET(response_model=_ResourceList)
    async def list_resource(
        self,
        repo: Annotated[CrudRepository[ModelT], Depends(repo)],
    ):
        return await repo.list_resources()

    @single.GET(
        response_model=_ResourceRead,
        dependencies=[Depends(access_org_reader)],
    )
    async def read_resource(
        self,
        resource_id: Annotated[UUID, Depends(resource_id)],
        repo: Annotated[CrudRepository[ModelT], Depends(repo)],
    ):
        return self.model.schemas().read.model_validate(
            await repo.get(resource_id), from_attributes=True
        )

    @single.PUT(
        response_model=_ResourceRead,
        dependencies=[Depends(access_org_contributor)],
    )
    async def update_resource(
        self,
        resource_id: Annotated[UUID, Depends(resource_id)],
        update: _UpdateResource,
        repo: Annotated[CrudRepository[ModelT], Depends(repo)],
    ):
        return await repo.update(resource_id, update)

    @single.DELETE(
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[Depends(access_org_owner)],
    )
    async def delete_resource(
        self,
        resource_id: Annotated[UUID, Depends(resource_id)],
        repo: Annotated[CrudRepository[ModelT], Depends(repo)],
    ) -> None:
        await repo.delete(resource_id)

    @access.GET(
        response_model=list[ResourceAccessItem],
        dependencies=[Depends(access_org_contributor)],
    )
    async def get_access(
        self,
        resource_id: Annotated[UUID, Depends(resource_id)],
        repo: Annotated[CrudRepository[ModelT], Depends(repo)],
    ) -> list[ResourceAccessItem]:
        return await repo.get_access(resource_id)

    @access_single.GET(
        response_model=ResourceAccessItem,
        dependencies=[Depends(access_org_contributor)],
    )
    async def get_access_one(
        self,
        resource_id: Annotated[UUID, Depends(resource_id)],
        user_id: UUID,
        repo: Annotated[CrudRepository[ModelT], Depends(repo)],
    ) -> ResourceAccessItem:
        return await repo.get_access_one(resource_id, user_id)

    @access.POST(
        response_model=list[ResourceAccessItem],
        dependencies=[Depends(access_org_owner)],
    )
    async def set_access(
        self,
        resource_id: Annotated[UUID, Depends(resource_id)],
        access: ResourceAccessItem | list[ResourceAccessItem],
        repo: Annotated[CrudRepository[ModelT], Depends(repo)],
    ) -> list[ResourceAccessItem]:
        if isinstance(access, ResourceAccessItem):
            access = [access]
        return await repo.set_access(resource_id, access)

    def setup_endpoints(self):
        for attr in dir(self):
            item = getattr(self, attr)

            params: EndpointParameters | None = getattr(
                item, const.CAULDRON_ENDPOINT_PARAMS, None
            )

            if params:
                annotations = item.__annotations__
                for annotation in annotations.items():
                    annotation_name, annotation_value = annotation
                    # Replace function annotations that are known placeholders
                    # With the real schema derived from the core model
                    if annotation_value == _CreateResource:
                        annotations[annotation_name] = self.model.schemas().create
                    if annotation_value == _UpdateResource:
                        annotations[annotation_name] = self.model.schemas().create
                    if annotation_value == _ResourceRead:
                        annotations[annotation_name] = self.model.schemas().read
                    if annotation_value == _ResourceList:
                        annotations[annotation_name] = list[
                            self.model.schemas().summary
                        ]

                    response_model = params.kwargs.get("response_model", None)
                    if response_model == _ResourceRead:
                        params.kwargs["response_model"] = self.model.schemas().read
                    if response_model == _ResourceList:
                        params.kwargs["response_model"] = list[
                            self.model.schemas().summary
                        ]

        super().setup_endpoints()
