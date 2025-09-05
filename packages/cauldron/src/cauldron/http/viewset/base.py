"""Base viewset ABC..

Viewsets are cauldron's basic entrypoint for handling HTTP requests.

The term is taken straight from Django Rest Framework as I think it is a clear way
to organize this layer of a web applocation.
They contain a set of related "views" or "endpoints"
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import make_dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, get_type_hints
from uuid import UUID

import structlog
from fastapi.params import Depends

from cauldron.http import APIRouter
from cauldron.http.viewset import (
    const,
    endpoints,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from enum import Enum
    from types import EllipsisType

    from pydantic import BaseModel

    CreateResource = BaseModel
    UpdateResource = BaseModel
    ResourceRead = BaseModel
    ResourceSummary = BaseModel

    _router = APIRouter()
    _UNUSED_PATH = "/unused"


logger = structlog.get_logger()

type ViewSetTags = Sequence[str | Enum]
type ViewSetDependencies = Sequence[Any]
type ViewSetBasePath = Sequence[str]


class PathParameterPlaceholder:
    """represents the path parameters of a request.

    This is used as a sentinel object, as a type hint,
    signalling that the viewset should compute the pathparameter
    dependency at instantiation by calling  self.get_path_param_name
    """


class AbstractViewSet(ABC):
    """The basic viewset base class.

    The intended use-cae of this is as a base for
    a more dynamic viewset.
    """

    tags: ViewSetTags = ()
    dependencies: ViewSetDependencies = ()
    base_path: ViewSetBasePath = ()

    def __init__(
        self,
        tags: ViewSetTags | None = None,
        dependencies: ViewSetDependencies | None = None,
        base_path: ViewSetBasePath | None = None,
    ):
        self.tags = tags or self.tags
        self.dependencies = dependencies or self.dependencies
        self.base_path = base_path or self.base_path
        self._router = APIRouter(
            tags=list(self.get_router_tags()), dependencies=self.get_dependencies()
        )
        self.setup_endpoints()

    @property
    def router(self) -> APIRouter:
        return self._router

    @abstractmethod
    def get_path_param_name(self) -> str:
        "Provide the name of the path parameter"

    def get_path_params_class(self):
        return make_dataclass(
            "InstancePathParams",
            [(self.get_path_param_name(), Annotated[UUID, Path()])],
        )

    def process_metadata_item(
        self, hint_name: str, item: Any, hint: Any, metadata: Any
    ):
        """Return bound instance of dependency if there is a bound instance available.

        Otherwise return the original dependency
        """
        if isinstance(metadata, Depends) and metadata.dependency:
            bound_dependency = getattr(self, metadata.dependency.__name__, None)
            if bound_dependency and metadata.dependency is bound_dependency.__func__:
                return Depends(bound_dependency)
        if (
            isinstance(metadata, Depends)
            and getattr(hint, "__origin__", None) is PathParameterPlaceholder
            and metadata.dependency is None
        ):
            item.__annotations__[hint_name] = Annotated[
                self.get_path_params_class(), Depends()
            ]
            return Depends()
        return metadata

    def setup_dependencies(self, item: Any):
        logger.debug(f"setting up dependencies for {item=}")
        hints = get_type_hints(item, include_extras=True)
        for hint_name, hint in hints.items():
            metadata = getattr(hint, "__metadata__", None)
            if metadata:
                hint.__metadata__ = tuple(
                    self.process_metadata_item(hint_name, item, hint, md)
                    for md in metadata
                )

    def _parse_path_component(self, component: str | EllipsisType):
        return "{" + self.get_path_param_name() + "}" if component is ... else component

    def setup_endpoint(
        self, attr: str, item: Any, params: endpoints.EndpointParameters
    ):
        path_params = [self._parse_path_component(p) for p in params.path]
        path = list(self.get_base_path()) + path_params
        path_obj = Path("/" + "/".join(path))
        path_str = str(path_obj) + "/" if params.trailing_slash else str(path_obj)
        logger.debug(f"Creating fastapi endpoint for {self=} {attr=} {item=}")
        wrapper: Callable[..., Any] = getattr(self.router, params.method.value.lower())
        logger.debug(f"wrapping {item=}")
        if deps := params.kwargs.get("dependencies"):
            params.kwargs["dependencies"] = [
                self.process_metadata_item(attr, item, None, dep) for dep in deps
            ]

        wrapper(path_str, *params.args, **params.kwargs)(item)

    def setup_endpoints(self):
        """required method called to configure the router."""
        for attr in dir(self):
            item = getattr(self, attr)
            if getattr(item, "__self__", None):
                self.setup_dependencies(item)
                params: endpoints.EndpointParameters | None = getattr(
                    item, const.CAULDRON_ENDPOINT_PARAMS, None
                )
                if params:
                    self.setup_endpoint(attr, item, params)

    @abstractmethod
    def get_base_path(self) -> Sequence[str]:
        """Give the components of the base path for all routes on the router."""

    @abstractmethod
    def get_dependencies(self) -> ViewSetDependencies:
        """required method called for viewset-wide dependencies"""

    @abstractmethod
    def get_router_tags(self) -> ViewSetTags:
        """required method called to determine the router tags"""


class ViewSet(AbstractViewSet):
    """A basic viewset with simple implementations of each required method.

    If you just want to write your own HTTP endpoints, this is the no-frills
    class-based viewset to use.
    """

    def __init__(
        self,
        tags: ViewSetTags | None = None,
        dependencies: ViewSetDependencies | None = None,
        base_path: ViewSetBasePath | None = None,
    ):
        self.tags = tags or self.tags
        self.dependencies = dependencies or self.dependencies
        self.base_path = base_path or self.base_path
        super().__init__()

    def get_path_param_name(self) -> str:
        "Provide the name of the path parameter"
        raise NotImplementedError(
            "The base viewset class does not permit the use of get_path_param_name. "
            "You need to override this method when subclassing to enable this."
        )

    def get_router_tags(self) -> ViewSetTags:
        return self.tags

    def get_dependencies(self) -> ViewSetDependencies:
        return self.dependencies

    def get_base_path(self) -> ViewSetBasePath:
        return self.base_path
