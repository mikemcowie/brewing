"""
Viewset - the basic building block for http handlers in brewing.

The viewset is a wrapper/facade around fastapi's APIRouter, with
the structure and terminology influenced by Django's views
and Django Rest Framework's viewsets.
"""

from __future__ import annotations

from types import EllipsisType
from fastapi import APIRouter
from brewing.http.path import HTTPPath, TrailingSlashPolicy
from brewing.http.annotations import (
    AnnotatedFunctionAdaptorPipeline,
    ApplyViewSetDependency,
)


class ViewSet:
    """A collection of related http endpoint handlers."""

    annotation_adaptors: AnnotatedFunctionAdaptorPipeline

    def __init__(
        self,
        root_path: str = "",
        router: APIRouter | None = None,
        trailing_slash_policy: TrailingSlashPolicy = TrailingSlashPolicy.default(),
    ):
        self.annotation_adaptors = (ApplyViewSetDependency(self),)
        self.router = router or APIRouter()
        self.root_path = HTTPPath(
            root_path,
            trailing_slash_policy=trailing_slash_policy,
            router=self.router,
            annotation_pipeline=self.annotation_adaptors,
        )
        self.trailing_slash_policy = trailing_slash_policy
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

    def __call__(
        self, path: str, trailing_slash: bool | EllipsisType = ...
    ) -> HTTPPath:
        """Create an HTTP path based on the root HTTPPath of the viewset."""
        return self.root_path(path, trailing_slash=trailing_slash)
