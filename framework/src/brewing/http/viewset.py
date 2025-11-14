"""
Viewset - the basic building block for http handlers in brewing.

The viewset is a wrapper/facade around fastapi's APIRouter, with
the structure and terminology influenced by Django's views
and Django Rest Framework's viewsets.
"""

from __future__ import annotations

from types import EllipsisType, FunctionType
from typing import Protocol
from dataclasses import replace, dataclass
from fastapi import APIRouter
from fastapi.params import Depends
from brewing.http.path import (
    HTTPPath,
    TrailingSlashPolicy,
    DeferredHTTPPath,
    DeferredDecoratorCall,
)
from brewing.http.annotations import (
    AnnotatedFunctionAdaptorPipeline,
    ApplyViewSetDependency,
    AnnotationState,
    adapt,
)


class ViewsetOptionsProtocol(Protocol):
    """Attributes that must be implemented for any viewset options object."""

    root_path: str
    trailing_slash_policy: TrailingSlashPolicy


@dataclass
class ViewsetOptions:
    """Minimal options class for a basic viewset."""

    root_path: str = ""
    trailing_slash_policy: TrailingSlashPolicy = TrailingSlashPolicy.default()


class ViewSet[OptionsT: ViewsetOptionsProtocol]:
    """A collection of related http endpoint handlers."""

    annotation_adaptors: AnnotatedFunctionAdaptorPipeline

    def __init__(
        self,
        viewset_options: OptionsT,
        router: APIRouter | None = None,
    ):
        self.viewset_options = viewset_options
        self.annotation_adaptors = (ApplyViewSetDependency(self),)
        self.router = router or APIRouter()
        self.root_path = HTTPPath(
            viewset_options.root_path,
            trailing_slash_policy=viewset_options.trailing_slash_policy,
            router=self.router,
            annotation_pipeline=self.annotation_adaptors,
        )
        self.trailing_slash_policy = viewset_options.trailing_slash_policy
        # All the HTTP method decorators from the router
        # are made directly available so it can be used with
        # exactly the same decorator syntax in a functional manner.
        self.get = self.router.get
        self.post = self.router.post
        self.head = self.router.head
        self.put = self.router.put
        self.patch = self.router.patch
        self.delete = self.router.delete
        self.options = self.router.options
        self.trace = self.router.trace
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
            if callable(getattr(self, m)) and not m[0] == "_"
        ]
        self._defferred_paths = [
            getattr(self, m)
            for m in dir(self)
            if isinstance(getattr(self, m), DeferredHTTPPath)
        ]
        self._rewrite_fastapi_style_depends()
        self._setup_classbased_endpoints()

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
                    value = replace(value, annotated=tuple(annotations_as_list))
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
