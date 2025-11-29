"""
Viewset - the basic building block for http handlers in brewing.

The viewset is a wrapper/facade around fastapi's APIRouter, with
the structure and terminology influenced by Django's views
and Django Rest Framework's viewsets.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import cached_property
from typing import TYPE_CHECKING

from fastapi import APIRouter
from fastapi.params import Depends

from brewing.http.path import base_path
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
from brewing.serialization import ExcludeCachedProperty
from brewing.db.repo import Repository

if TYPE_CHECKING:
    from enum import Enum
    from types import EllipsisType, FunctionType

    from starlette.routing import BaseRoute
    from  sqlalchemy.orm import DeclarativeBase

# ruff: noqa: N802


@dataclass
class ViewSet(ExcludeCachedProperty):
    """A collection of related http endpoint handlers."""

    path: str = ""
    trailing_slash_policy: TrailingSlashPolicy = field(
        default_factory=TrailingSlashPolicy
    )
    tags: list[str | Enum] | None = None

    def __post_init__(self):
        self._rewrite_fastapi_style_depends()
        self._setup_classbased_endpoints()

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
        return (ApplyViewSetDependency(self),)

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

    def _all_methods(self):
        return [
            getattr(self, m)
            for m in dir(self)
            if callable(getattr(self, m)) and m[0] != "_"
        ]

    def _rewrite_fastapi_style_depends(self):
        for method in self._all_methods():
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
                            getattr(f, "__func__", ...) for f in self._all_methods()
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
            for m in self._all_methods()
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


class BaseModelViewset[ModelT:DeclarativeBase, LookupT]:
    """A base model viewset with no endpoints implemented."""
    model:type[ModelT]
    lookup_type:type[LookupT]

    def __post_init__(self):
        self.repo = Repository[self.model, self.lookup_type]()


UpdateType = ... ## TODO - make a sentinel update model type hint mechanism

class ModelViewSet[ModelT:DeclarativeBase, LookupT](BaseModelViewset[ModelT, LookupT]):
    """A viewset with basic CRUD methods based on a model."""


    instance_path = base_path("{model_var_placeholder}")

    @base_path.POST()
    async def create(self, item:ModelT):
        return await self.repo.create(item)

    @base_path.GET()
    async def query(self):
        return await self.repo.execute(self.repo.query())

    async def get_item(self, item_id:LookupT):
        return await self.repo.get(item_id)

    @instance_path.GET()
    async def get_one(self, item_id:LookupT):
        return await self.get_item(item_id)

    @instance_path.PUT()
    async def update_one(self, item_id:LookupT, **update:UpdateType):
        return await self.repo.update(await self.get_item(item_id), **update)

    @instance_path.PATCH()
    async def update_one_partial(self, item_id:LookupT, **update:PartialUpdateType):
        return await self.repo.update(await self.get_item(item_id), **update)

    @instance_path.DELETE()
    async def delete_one(self, item_id:LookupT):
        return await self.repo.delete(await self.get_item(item_id))
