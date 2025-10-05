"""
The endpoint decorator implementation.

This creates an endpoint decorator for each HTTP method.
It wraps around fastapi's endpoint decorator.
"""

from __future__ import annotations

from typing import Callable, Any, TYPE_CHECKING, Protocol, cast
from http import HTTPMethod
from fastapi.routing import APIRouter
from fastapi import Depends
from fastapi.params import Depends as DependsParam

if TYPE_CHECKING:
    from brewing.http.path import HTTPPath


type AnyCallable = Callable[..., Any]


class RouteProtocol(Protocol):
    """
    Protocol for our use of fastapi's APIRoute.

    Used for type hints because fastapi's Route objects
    are typed as starlette BaseRoute attributes, but have extra
    runtime attributes added that we depend on.
    """

    dependencies: list[DependsParam]
    path: str


class DependencyDecorator:
    """Register a dependency for the current route - i.e. code theat will run for all HTTP methods."""

    def __init__(self, router: APIRouter, path: HTTPPath):
        self.router = router
        self.path = path
        self.dependencies: list[Callable[..., Any]] = []

    def apply(self):
        """Apply all dependencies of path to all routes."""
        for route in cast(list[RouteProtocol], self.router.routes):
            assert isinstance(route.dependencies, list)
            current_deps = [dep.dependency for dep in route.dependencies]
            for func in self.dependencies:
                if all(
                    (
                        func not in current_deps,
                        route,
                        route.path.startswith(str(self.path)),
                    )
                ):
                    route.dependencies.append(Depends(func))

    def __call__(self, func: Callable[..., Any]):
        """Apply dependency func to all endpoints, current and future, of the given path."""
        self.dependencies.append(func)
        self.apply()
        return func


class EndpointDecorator:
    """Provide an upper-case decorator that serves as brewing's native endpoint decorator."""

    def __init__(self, method: HTTPMethod, path: HTTPPath):
        self.path = path
        self.wraps = getattr(path.router, method.value.lower())

    def __call__(self, *args: Any, **kwargs: Any):
        """Register a route for the object's path and the given HTTP method."""
        retval = self.wraps(str(self.path), *args, **kwargs)
        self.path.DEPENDS.apply()
        return retval
