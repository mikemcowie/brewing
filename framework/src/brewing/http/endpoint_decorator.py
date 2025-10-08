"""
The endpoint decorator implementation.

This creates an endpoint decorator for each HTTP method.
It wraps around fastapi's endpoint decorator.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable, Any, TYPE_CHECKING, Protocol, cast
from types import FunctionType
from http import HTTPMethod
from fastapi.routing import APIRouter
from fastapi import Depends
from fastapi.params import Depends as DependsParam
from brewing.http.annotations import adapt, AnnotatedFunctionAdaptorPipeline


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

    def __call__(
        self,
    ):
        """Apply dependency func to all endpoints, current and future, of the given path."""
        # To maintain a visual consistency between DEPENDS and GET/POST etc decorators
        # This is implemented as a decorator factory rather than decorator.
        # Currently there are no parameters, though it would not be insane to add some.

        def inner(func: Callable[..., Any]):
            self.dependencies.append(func)
            self.apply()
            return func

        return inner


class EndpointDecorator:
    """Provide an upper-case decorator that serves as brewing's native endpoint decorator."""

    def __init__(
        self,
        method: HTTPMethod,
        path: HTTPPath,
        annotation_pipeline: AnnotatedFunctionAdaptorPipeline = (),
    ):
        self.path = path
        self.annotation_pipeline = annotation_pipeline
        self.wraps = getattr(path.router, method.value.lower())

    def __call__(self, *args: Any, **kwargs: Any):
        """Register a route for the object's path and the given HTTP method."""
        retval = self.endpoint_function_wrapper(self.wraps)(
            str(self.path), *args, **kwargs
        )
        self.path.DEPENDS.apply()
        return retval

    def endpoint_function_wrapper(self, func: FunctionType):
        """
        Adapted fastapi endpoint wrapper.

        Applies additional step from the usual fastapi endpoint decorator:
        adapts the type annotations of the wrapped function.
        """
        adapt(func, self.annotation_pipeline)

        # In future some annotation handlers will require a transformation of
        # args and kwargs before passing to the handled function, so in anticipation,
        # return a wrapped function instead of the original function.
        @wraps(func)
        def inner(*args: Any, **kwargs: Any):
            return func(*args, **kwargs)

        return inner
