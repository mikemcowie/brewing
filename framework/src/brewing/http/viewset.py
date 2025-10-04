"""
Viewset - the basic building block for http handlers in brewing.

The viewset is a wrapper/facade around fastapi's APIRouter, with
the structure and terminology influenced by Django's views
and Django Rest Framework's viewsets.
"""

from __future__ import annotations

from typing import Callable, Any
from types import EllipsisType
from fastapi import APIRouter
from http import HTTPMethod
from brewing.http.path import HTTPPath, TrailingSlashPolicy


type AnyCallable = Callable[..., Any]


class EndpointDecorator:
    """Provide an upper-case decorator that serves as brewing's native endpoint decorator."""

    def __init__(self, method: HTTPMethod, wraps: AnyCallable):
        self.method = method
        self.wraps = wraps

    def __call__(self, *outer_args, **outer_kwargs):
        first = outer_args[0]
        if isinstance(first, str):

            def _middle(func: AnyCallable):
                def _inner(*inner_args, **inner_kwargs):
                    return func(*inner_args, **inner_kwargs)

                return _inner

            return _middle
        if callable(first):

            def _inner(*inner_args, **inner_kwargs):
                return first(*inner_args, **inner_kwargs)

            return _inner
        raise TypeError("First parameter should be a string or callable.")


class ViewSet:
    """A collection of related http endpoint handlers."""

    def __init__(
        self,
        root_path: str = "",
        router: APIRouter | None = None,
        trailing_slash_policy: TrailingSlashPolicy = TrailingSlashPolicy.default(),
    ):
        self._router = router or APIRouter()
        self.root_path = HTTPPath(
            root_path, trailing_slash_policy=trailing_slash_policy, router=self._router
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

    @property
    def router(self):
        """The underlying fastapi router."""
        return self._router

    def __call__(self, path: str, trailing_slash: bool | EllipsisType = ...) -> Any:
        return self.root_path(path, trailing_slash=trailing_slash)
