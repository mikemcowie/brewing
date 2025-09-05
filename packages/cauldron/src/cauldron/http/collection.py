"""Method decoratotors.

Viewset methods are decorated with objects from this module to define endpoints.
These methods wrap around fastapi's router methods in a class-based context.
"""

from __future__ import annotations

from functools import partial
from http import HTTPMethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from cauldron.http import APIRouter

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
