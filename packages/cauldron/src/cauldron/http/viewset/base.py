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


class AbstractViewSet(ABC):
    """The basic viewset base class.

    It contains a partial implementation that may be used
    via inheritence, though this is entirely optional.
    """

    def __init__(self):
        self._router = APIRouter(
            tags=self.get_router_tags(), dependencies=self.get_router_dependencies()
        )
        self._router.dependency_overrides_provider = {}
        self.setup_endpoints()

    @property
    def router(self) -> APIRouter:
        return self._router

    def setup_endpoints(self):
        """required method called to configure the router."""
        for attr in dir(self):
            item = getattr(self, attr)
            params: endpoints.EndpointParameters | None = getattr(
                item, "_cauldron_endpoint_params", None
            )
            if params:
                path_parts = list(self.get_base_path()) + list(params.path.parts)
                path = Path("/", "/".join(path_parts))
                path_str = str(path) + "/" if params.trailing_slash else str(path)
                logger.debug(f"Creating fastapi endpoint for {self=} {attr=} {item=}")
                wrapper: Callable[..., Any] = getattr(
                    self.router, params.method.value.lower()
                )
                wrapper(path_str, *params.args, **params.kwargs)(item)

    @abstractmethod
    def get_base_path(self) -> Sequence[str]:
        """Give the components of the base path for all routes on the router."""

    @abstractmethod
    def get_router_dependencies(self) -> Sequence[Any]:
        """required method called to determine the router tags"""

    @abstractmethod
    def get_router_tags(self) -> list[str | Enum]:
        """required method called to determine the router tags"""
