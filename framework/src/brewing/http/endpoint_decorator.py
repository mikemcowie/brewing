"""
The endpoint decorator implementation.

This creates an endpoint decorator for each HTTP method.
It wraps around fastapi's endpoint decorator.
"""

from __future__ import annotations

from typing import Callable, Any, Literal
from http import HTTPMethod
from fastapi.routing import APIRouter


type AnyCallable = Callable[..., Any]


def _depends_placeholder(*_, **__):
    """WIP placeholder for DEPENDS 'method'."""


class EndpointDecorator:
    """Provide an upper-case decorator that serves as brewing's native endpoint decorator."""

    def __init__(self, method: HTTPMethod | Literal["DEPENDS"], router: APIRouter):
        if method == "DEPENDS":
            self.wraps = _depends_placeholder
        else:
            self.wraps = getattr(router, method.value.lower())

    def __call__(self, *args, **kwargs):
        return self.wraps(*args, **kwargs)
