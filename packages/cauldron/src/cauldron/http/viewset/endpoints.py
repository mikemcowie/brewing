"""Core viewset classes.

Viewsets are cauldron's basic entrypoint for handling HTTP requests.

The term is taken straight from Django Rest Framework as I think it is a clear way
to organize this layer of a web applocation.
They contain a set of related "views" or "endpoints"
"""

from __future__ import annotations

import string
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from http import HTTPMethod as HTTPMethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pydantic import BaseModel

    from cauldron.http import APIRouter

    CreateResource = BaseModel
    UpdateResource = BaseModel
    ResourceRead = BaseModel
    ResourceSummary = BaseModel

    from collections.abc import Callable

    _router = APIRouter()
    _UNUSED_PATH = "/unused"


@dataclass
class EndpointParameters:
    trailing_slash: bool
    path: Path
    method: HTTPMethod
    args: Sequence[Any]
    kwargs: dict[str, Any]


class EndpointDecoratorMaker:
    def __init__(self, path: Sequence[str], *, trailing_slash: bool):
        self.trailing_slash = trailing_slash
        self.path = [p for p in path if p]
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

    def _method(self, wrappedmethod: HTTPMethod, *args: Any, **kwargs: Any):
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
            path = Path("/", *self.path)
            path = path / "/" if self.trailing_slash else path
            func.__dict__["_cauldron_endpoint_params"] = EndpointParameters(
                path=path,
                trailing_slash=self.trailing_slash,
                method=wrappedmethod,
                args=args,
                kwargs=kwargs,
            )
            return func

        return decorator

    def path_parameter(self, param_name: str) -> EndpointDecoratorMaker:
        return EndpointDecoratorMaker(
            [*self.path, APIPathParam(param_name)], trailing_slash=False
        )

    def action(self, param_name: str) -> EndpointDecoratorMaker:
        return EndpointDecoratorMaker(
            [*self.path, APIPathComponent(param_name)], trailing_slash=False
        )


collection = EndpointDecoratorMaker([], trailing_slash=True)


class APIPathComponent(str):
    """A component of an api path

    i.e. in fastapi-style path /things/{thing_id}
    is broken into path components 'things' and 'thing_id'
    with the former being an APIPathConstant and the latter being an
    APIPathParam
    """

    _ALLOWED_CHARS = string.ascii_letters + string.digits + "-" + "_" + "{}"

    def __new__(cls, value: str):
        if not set(cls._ALLOWED_CHARS).issuperset(value):
            raise ValueError(
                f"invalid characters for path component in {value}, {set(value).difference(cls._ALLOWED_CHARS)}"
            )
        return str(value)


class APIPathConstant(APIPathComponent):
    """A component of an api path that is constant.

    e.g.. in /things/{thing_id}, things is a path constant.
    """

    def __new__(cls, value: str):
        if set("{}").intersection(value):
            raise ValueError(
                f"Cannot use '{' or '}' in constant path segments in value {value}"
            )
        return super().__new__(cls, value)


class APIPathParam(APIPathComponent):
    """A component of an api path that varies

    e.g.. in /things/{thing_id}, thing_id is a path param.
    """

    def __new__(cls, value: str):
        return super().__new__(cls, "{" + value + "}")
