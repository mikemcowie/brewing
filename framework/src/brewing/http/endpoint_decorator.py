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


class Dependency:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __call__(self, func, *args, **kwargs):
        return func


def dependency(*args, **kwargs):
    """WIP placeholder for DEPENDS 'method'."""
    return Dependency(*args, **kwargs)


class EndpointDecorator:
    """Provide an upper-case decorator that serves as brewing's native endpoint decorator."""

    def __init__(
        self, method: HTTPMethod | Literal["DEPENDS"], router: APIRouter, path: str
    ):
        self.path = path
        if method == "DEPENDS":
            self.wraps = dependency
        else:
            self.wraps = getattr(router, method.value.lower())

    def __call__(self, first_arg: Any, *args, **kwargs):
        if not callable(first_arg):
            return self.wraps(first_arg, *args, **kwargs)
        return self.wraps(self.path, *args, **kwargs)(first_arg)
