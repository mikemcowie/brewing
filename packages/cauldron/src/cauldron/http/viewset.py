"""Core viewset classes.

Viewsets are cauldron's basic entrypoint for handling HTTP requests.

The term is taken straight from Django Rest Framework as I think it is a clear way
to organize this layer of a web applocation.
They contain a set of related "views" or "endpoints"
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING, Any

from cauldron.http import APIRouter

if TYPE_CHECKING:
    from pydantic import BaseModel

    CreateResource = BaseModel
    UpdateResource = BaseModel
    ResourceRead = BaseModel
    ResourceSummary = BaseModel


class AbstractViewSet(ABC):
    """The basic viewset base class.

    It contains a partial implementation that may be used
    via inheritence, though this is entirely optional.
    """

    def __init__(self):
        self._router = APIRouter(
            tags=self.get_router_tags(), dependencies=self.get_router_dependencies()
        )
        self.setup_endpoints()

    @property
    def router(self) -> APIRouter:
        return self._router

    @abstractmethod
    def setup_endpoints(self):
        """required method called to configure the router."""

    @abstractmethod
    def get_router_dependencies(self) -> Sequence[Any]:
        """required method called to determine the router tags"""

    @abstractmethod
    def get_router_tags(self) -> list[str | Enum]:
        """required method called to determine the router tags"""
