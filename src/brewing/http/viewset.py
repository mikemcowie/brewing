"""
Viewset - the basic building block for http handlers in brewing.

The viewset is a wrapper/facade around fastapi's APIRouter, with
the structure and terminology influenced by Django's views
and Django Rest Framework's viewsets.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import cached_property
from types import EllipsisType, FunctionType, MethodType
from typing import TYPE_CHECKING, Any, ClassVar

from fastapi import APIRouter
from fastapi.params import Depends

from brewing.http.annotations import (
    AnnotationState,
    ApplyViewSetDependency,
    WrapCustomSerializers,
    adapt,
)
from brewing.http.path import (
    DeferredDecoratorCall,
    DeferredHTTPPath,
    HTTPPath,
    TrailingSlashPolicy,
)
from brewing.serialization import ExcludeCachedProperty

if TYPE_CHECKING:
    from collections.abc import Callable
    from enum import Enum

    from starlette.routing import BaseRoute

# ruff: noqa: N802


@dataclass
class ViewSet(ExcludeCachedProperty):
    """A collection of related http endpoint handlers."""

    path: str = ""
    trailing_slash_policy: TrailingSlashPolicy = field(
        default_factory=TrailingSlashPolicy
    )
    tags: list[str | Enum] | None = None

    _original_annotations: ClassVar[dict[Callable[..., Any], dict[str, Any]]] = {}

    def __post_init__(self):
        self._generic_class_params = tuple(
            p.__name__ for p in self.__class__.__type_params__
        )
        if self._generic_class_params:
            # TODO: WIP
            raise Exception(
                {
                    k: v
                    for k, v in self.__class__.__annotations__.items()
                    if v in [f"type[{p}]" for p in self._generic_class_params]
                }
            )
        self._methods = [
            method
            for method in (
                getattr(self, m, None)
                for m in dir(self)
                if m[0] != "_" and m not in dir(ViewSet)
            )
            if isinstance(method, MethodType)
        ]
        if not self._original_annotations:
            for method in self._methods:
                self._original_annotations[method.__func__] = (
                    method.__annotations__.copy()
                )
        for method in self._methods:
            self._rewrite_fastapi_style_depends(method)
        func: FunctionType
        calls: list[DeferredDecoratorCall]
        for func, calls in [  # type: ignore
            (m, getattr(m, DeferredHTTPPath.METADATA_KEY, None))
            for m in self._methods
            if getattr(m, DeferredHTTPPath.METADATA_KEY, None)
        ]:
            self._setup_classbased_endpoints(func, calls)

    @cached_property
    def GET(self):
        return self.root_path.GET

    @cached_property
    def POST(self):
        return self.root_path.POST

    @cached_property
    def PUT(self):
        return self.root_path.PUT

    @cached_property
    def PATCH(self):
        return self.root_path.PATCH

    @cached_property
    def DELETE(self):
        return self.root_path.DELETE

    @cached_property
    def HEAD(self):
        return self.root_path.HEAD

    @cached_property
    def OPTIONS(self):
        return self.root_path.OPTIONS

    @cached_property
    def TRACE(self):
        return self.root_path.TRACE

    @cached_property
    def DEPENDS(self):
        return self.root_path.DEPENDS

    @cached_property
    def annotation_adaptors(self):
        return (ApplyViewSetDependency(self), WrapCustomSerializers(self))

    @cached_property
    def root_path(self):
        return HTTPPath(
            self.path,
            trailing_slash_policy=self.trailing_slash_policy,
            router=self.router,
            annotation_pipeline=self.annotation_adaptors,
        )

    @cached_property
    def router(self):
        return APIRouter(tags=self.tags)

    @property
    def routes(self) -> tuple[BaseRoute, ...]:
        """Expose, immutably, the starlette routes associated with the viewset."""
        return tuple(self.router.routes)

    def _rewrite_fastapi_style_depends(self, method: MethodType):
        try:
            annotation_state = AnnotationState(method)
        except TypeError:
            # Just indicates its not an item we need to handle
            return
        for key, value in annotation_state.hints.items():
            annotations_as_list = list(value.annotated)
            for annotation in value.annotated:
                if isinstance(annotation, Depends) and annotation.dependency in [
                    getattr(f, "__func__", ...) for f in self._methods
                ]:
                    annotations_as_list.remove(annotation)
                    annotations_as_list.append(
                        Depends(getattr(self, annotation.dependency.__name__))  # type: ignore
                    )
            value = replace(value, annotated=tuple(annotations_as_list))  # noqa: PLW2901
            annotation_state.hints[key] = value
        annotation_state.apply_pending()

    def _setup_classbased_endpoints(
        self, endpoint_func: FunctionType, calls: list[DeferredDecoratorCall]
    ):
        func = adapt(endpoint_func.__func__, self.annotation_adaptors)  # type: ignore
        for call in calls:
            http_path = call.path.apply(self, call)
            decorator_factory = getattr(http_path, call.method)
            decorator = decorator_factory(*call.args, **call.kwargs)
            # Fastapi looks at the __wrapped__ attribute for type hints
            # if it exists
            if wrapped := getattr(func, "__wrapped__", None):
                wrapped.__annotations__ = func.__annotations__
            decorator(func)  # type: ignore
        self._restore_original_annotations()

    @classmethod
    def _restore_original_annotations(cls):
        for func, value in cls._original_annotations.items():
            func.__annotations__ = value

    def __call__(
        self, path: str, trailing_slash: bool | EllipsisType = ...
    ) -> HTTPPath:
        """Create an HTTP path based on the root HTTPPath of the viewset."""
        return self.root_path(path, trailing_slash=trailing_slash)
