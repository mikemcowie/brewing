"""
The endpoint decorator implementation.

This creates an endpoint decorator for each HTTP method.
It wraps around fastapi's endpoint decorator.
"""

from __future__ import annotations

from typing import Callable, Any, TYPE_CHECKING
from http import HTTPMethod
from fastapi.routing import APIRouter
from fastapi import Depends

if TYPE_CHECKING:
    from brewing.http.path import HTTPPath


type AnyCallable = Callable[..., Any]


class DependencyDecorator:
    """Register a dependency for the current route - i.e. code theat will run for all HTTP methods."""

    def __init__(self, router: APIRouter, path: HTTPPath):
        self.router = router
        self.path = path
        self.dependencies: list[Callable[..., Any]] = []

    def apply(self):
        """Apply all dependencies of path to all routes."""
        for route in self.router.routes:
            assert isinstance(route.dependencies, list)  # type: ignore[reportAttributeAccessIssue]
            current_deps = [dep.dependency for dep in route.dependencies]  # type: ignore[reportAttributeAccessIssue]
            for func in self.dependencies:
                if func not in current_deps and route:
                    route.dependencies.append(Depends(func))  # type: ignore[reportAttributeAccessIssue]

    def __call__(self, func: Callable[..., Any], *args: Any, **kwargs: Any):
        """Apply dependency func to all endpoints, current and future, of the given path."""
        self.dependencies.append(func)
        self.apply()
        return func


class EndpointDecorator:
    """Provide an upper-case decorator that serves as brewing's native endpoint decorator."""

    def __init__(self, method: HTTPMethod, path: HTTPPath):
        self.path = path
        self.wraps = getattr(path.router, method.value.lower())

    def __call__(self, first_arg: Any, *args: Any, **kwargs: Any):
        """Register a route for the object's path and the given HTTP method."""
        if not callable(first_arg):
            retval = self.wraps(first_arg, *args, **kwargs)
        else:
            retval = self.wraps(str(self.path), *args, **kwargs)(first_arg)
        self.path.DEPENDS.apply()
        return retval
