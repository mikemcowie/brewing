"""Base viewset ABC..

Viewsets are cauldron's basic entrypoint for handling HTTP requests.

The term is taken straight from Django Rest Framework as I think it is a clear way
to organize this layer of a web applocation.
They contain a set of related "views" or "endpoints"
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from cauldron.http import APIRouter

if TYPE_CHECKING:
    from collections.abc import Sequence
    from enum import Enum

    from pydantic import BaseModel

    from cauldron.http.viewset import endpoints

    CreateResource = BaseModel
    UpdateResource = BaseModel
    ResourceRead = BaseModel
    ResourceSummary = BaseModel

    from collections.abc import Callable

    _router = APIRouter()
    _UNUSED_PATH = "/unused"


logger = structlog.get_logger()

type ViewSetTags = Sequence[str | Enum]
type ViewSetDependencies = Sequence[Any]
type ViewSetBasePath = Sequence[str]


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
        self._router.dependency_overrides_provider = {}
        self.setup_endpoints()

    @property
    def router(self) -> APIRouter:
        return self._router

    def setup_endpoint(
        self, attr: str, item: Any, params: endpoints.EndpointParameters
    ):
        path_parts = list(self.get_base_path()) + list(params.path.parts)
        path = Path("/", "/".join(path_parts))
        path_str = str(path) + "/" if params.trailing_slash else str(path)
        logger.debug(f"Creating fastapi endpoint for {self=} {attr=} {item=}")
        wrapper: Callable[..., Any] = getattr(self.router, params.method.value.lower())
        logger.info(f"wrapping {item=}")
        wrapper(path_str, *params.args, **params.kwargs)(item)

    def setup_endpoints(self):
        """required method called to configure the router."""
        for attr in dir(self):
            item = getattr(self, attr)
            params: endpoints.EndpointParameters | None = getattr(
                item, "_cauldron_endpoint_params", None
            )
            if params:
                self.setup_endpoint(attr, item, params)

    @abstractmethod
    def get_base_path(self) -> ViewSetBasePath:
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

    def get_router_tags(self) -> ViewSetTags:
        return self.tags

    def get_dependencies(self) -> ViewSetDependencies:
        return self.dependencies

    def get_base_path(self) -> ViewSetBasePath:
        return self.base_path
