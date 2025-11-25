"""
Viewset - the basic building block for http handlers in brewing.

The viewset is a wrapper/facade around fastapi's APIRouter, with
the structure and terminology influenced by Django's views
and Django Rest Framework's viewsets.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from fastapi import APIRouter
from fastapi.params import Depends

from brewing.http.annotations import (
    AnnotationState,
    ApplyViewSetDependency,
    adapt,
)
from brewing.http.path import (
    DeferredDecoratorCall,
    DeferredHTTPPath,
    HTTPPath,
    TrailingSlashPolicy,
)

if TYPE_CHECKING:
    from types import EllipsisType, FunctionType

    from starlette.routing import BaseRoute


@dataclass
class ViewSet:
    """A collection of related http endpoint handlers."""

    path: str = ""
    trailing_slash_policy: TrailingSlashPolicy = TrailingSlashPolicy.default()

    def __post_init__(self):
        self.annotation_adaptors = (ApplyViewSetDependency(self),)
        self.router = APIRouter()
        self.root_path = HTTPPath(
            self.path,
            trailing_slash_policy=self.trailing_slash_policy,
            router=self.router,
            annotation_pipeline=self.annotation_adaptors,
        )
        # The upper-case method names are brewing-specific
        # Meaning they compute the path off their context
        # instead of having the path passed as an explicit positional
        # parameter.
        # They are taken off the root_path object
        # which guarentees the same behaviour when the decorator
        # is used from a sub-path compared to the viewset itself.
        self.GET = self.root_path.GET
        self.POST = self.root_path.POST
        self.PUT = self.root_path.PUT
        self.PATCH = self.root_path.PATCH
        self.DELETE = self.root_path.DELETE
        self.HEAD = self.root_path.HEAD
        self.OPTIONS = self.root_path.OPTIONS
        self.TRACE = self.root_path.TRACE
        self.DEPENDS = self.root_path.DEPENDS
        self._all_methods = [
            getattr(self, m)
            for m in dir(self)
            if callable(getattr(self, m)) and m[0] != "_"
        ]
        self._defferred_paths = [
            getattr(self, m)
            for m in dir(self)
            if isinstance(getattr(self, m), DeferredHTTPPath)
        ]
        self._rewrite_fastapi_style_depends()
        self._setup_classbased_endpoints()

    @property
    def routes(self) -> tuple[BaseRoute, ...]:
        """Expose, immutably, the starlette routes associated with the viewset."""
        return tuple(self.router.routes)

    def _rewrite_fastapi_style_depends(self):
        for method in self._all_methods:
            try:
                annotation_state = AnnotationState(method)
            except TypeError:
                # Just indicates its not an item we need to handle
                continue
            for key, value in annotation_state.hints.items():
                if value.annotated:
                    annotations_as_list = list(value.annotated)
                    for annotation in value.annotated:
                        if isinstance(
                            annotation, Depends
                        ) and annotation.dependency in [
                            getattr(f, "__func__", ...) for f in self._all_methods
                        ]:
                            annotations_as_list.remove(annotation)
                            annotations_as_list.append(
                                Depends(getattr(self, annotation.dependency.__name__))  # type: ignore
                            )
                    value = replace(value, annotated=tuple(annotations_as_list))  # noqa: PLW2901
                annotation_state.hints[key] = value
            annotation_state.apply_pending()

    def _setup_classbased_endpoints(self):
        decorated_methods: list[tuple[FunctionType, list[DeferredDecoratorCall]]] = [  # type: ignore
            (m, getattr(m, DeferredHTTPPath.METADATA_KEY, None))
            for m in self._all_methods
            if getattr(m, DeferredHTTPPath.METADATA_KEY, None)
        ]
        for decorated_method in decorated_methods:
            endpoint_func, calls = decorated_method
            adapt(endpoint_func.__func__, self.annotation_adaptors)  # type: ignore
            for call in calls:
                http_path = call.path.apply(self, call)
                decorator_factory = getattr(http_path, call.method)
                decorator = decorator_factory(*call.args, **call.kwargs)
                decorator(endpoint_func.__func__)  # type: ignore

    def __call__(
        self, path: str, trailing_slash: bool | EllipsisType = ...
    ) -> HTTPPath:
        """Create an HTTP path based on the root HTTPPath of the viewset."""
        return self.root_path(path, trailing_slash=trailing_slash)
