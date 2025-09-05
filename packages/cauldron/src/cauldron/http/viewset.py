"""Core viewset classes.

Viewsets are cauldron's basic entrypoint for handling HTTP requests.

The term is taken straight from Django Rest Framework as I think it is a clear way
to organize this layer of a web applocation.
They contain a set of related "views" or "endpoints"
"""

from __future__ import annotations

import string
from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import partial
from http import HTTPMethod
from typing import TYPE_CHECKING, Any

import structlog

from cauldron.http import APIRouter

if TYPE_CHECKING:
    from collections.abc import Sequence
    from enum import Enum

    from pydantic import BaseModel

    CreateResource = BaseModel
    UpdateResource = BaseModel
    ResourceRead = BaseModel
    ResourceSummary = BaseModel

    from collections.abc import Callable

    _router = APIRouter()
    _UNUSED_PATH = "/unused"


class _Collection:
    def __init__(self, path: str):
        self.path = path
        # We trick IDEs to be more helpful for the near-complete spec of a Fastapi endpoint decorator
        # Except without the "path" part
        # by showing it an entirely different reality to the actual implementation...
        self.GET = (
            partial(_router.get, _UNUSED_PATH)
            if TYPE_CHECKING
            else partial(self._method, HTTPMethod.GET)
        )
        self.POST = (
            partial(_router.post, _UNUSED_PATH)
            if TYPE_CHECKING
            else partial(self._method, HTTPMethod.POST)
        )
        self.PUT = (
            partial(_router.put, _UNUSED_PATH)
            if TYPE_CHECKING
            else partial(self._method, HTTPMethod.PUT)
        )
        self.PATCH = (
            partial(_router.patch, _UNUSED_PATH)
            if TYPE_CHECKING
            else partial(self._method, HTTPMethod.PATCH)
        )
        self.DELETE = (
            partial(_router.delete, _UNUSED_PATH)
            if TYPE_CHECKING
            else partial(self._method, HTTPMethod.DELETE)
        )
        self.HEAD = (
            partial(_router.head, _UNUSED_PATH)
            if TYPE_CHECKING
            else partial(self._method, HTTPMethod.HEAD)
        )
        self.OPTIONS = (
            partial(_router.options, _UNUSED_PATH)
            if TYPE_CHECKING
            else partial(self._method, HTTPMethod.OPTIONS)
        )

    def _method(self: _Collection, wrappedmethod: HTTPMethod, *args, **kwargs):
        """Our own endpoint method decorator.

        The public interface to it is the http-method based partials which prepopulate
        the method field, and are typed to resemble fastapi's function decorators.

        In order to apply a fastapi-based decorator in a class-based context,
        we add metadata to the endpoint method at class declaration time,
        and then at instantiation we use it to apply the fastapi route decorator
        "manually". The effect is an interface nearly preserving fastapi's endpoint
        syntax - with fastapi's signature clear to IDEs and type-checkers - but behaving
        inside the class because the fastapi machinery gets delayed until
        until an instance of the viewset is created.
        """

        def decorator(func: Callable[..., Any]):
            func.__dict__["_cauldron_endpoint_params"] = {
                "path": self.path,
                "method": wrappedmethod.value,
                "args": args,
                "kwargs": kwargs,
            }
            return func

        return decorator


collection = _Collection("/")


logger = structlog.get_logger()


class APIPathComponent(str):
    """A component of an api path

    i.e. in fastapi-style path /things/{thing_id}
    is broken into path components 'things' and 'thing_id'
    with the former being an APIPathConstant and the latter being an
    APIPathParam
    """

    _ALLOWED_CHARS = string.ascii_letters + string.digits + "-" + "_"

    def __new__(cls, value: str):
        if not set(cls._ALLOWED_CHARS).issuperset(value):
            raise ValueError(
                f"invalid characters for path component in {value}, {set(value).difference(cls._ALLOWED_CHARS)}"
            )
        return cls(value)


class APIPathConstant(APIPathComponent):
    """A component of an api path that is constant.

    e.g.. in /things/{thing_id}, things is a path constant.
    """

    pass


class APIPathParam(APIPathComponent):
    """A component of an api path that varies

    e.g.. in /things/{thing_id}, thing_id is a path param.
    """

    def __new__(cls, value: str):
        return super().__new__(cls, "{" + value + "}")


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

    def setup_endpoints(self):
        """required method called to configure the router."""
        for attr in dir(self):
            item = getattr(self, attr)
            params: dict[str, Any] = getattr(item, "_cauldron_endpoint_params", {})
            if params:
                logger.debug(f"Creating fastapi endpoint for {self=} {attr=} {item=}")
                wrapper: Callable[..., Any] = getattr(
                    self.router, params["method"].lower()
                )
                wrapper(params["path"], *params["args"], **params["kwargs"])(item)

    @abstractmethod
    def get_base_path(self) -> Sequence[APIPathConstant | APIPathParam]:
        """Give the components of the base path for all routes on the router."""

    @abstractmethod
    def get_router_dependencies(self) -> Sequence[Any]:
        """required method called to determine the router tags"""

    @abstractmethod
    def get_router_tags(self) -> list[str | Enum]:
        """required method called to determine the router tags"""
