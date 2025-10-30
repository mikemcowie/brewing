"""
The Brewing ASGI application.

It is a shallow wrapper around fastapi with extra methods to support native features.
"""

from __future__ import annotations
import inspect
from typing import TYPE_CHECKING, Any, Self
from fastapi import FastAPI

if TYPE_CHECKING:
    from . import ViewSet


def find_calling_module():
    """Inspect the stack frame and return the module that called this."""
    frame = inspect.currentframe()
    while True:
        assert frame
        frame = frame.f_back
        module = inspect.getmodule(frame)
        assert module
        mod_name = module.__name__
        if mod_name != __name__:
            return mod_name


class BrewingHTTP(FastAPI):
    """
    The brewing ASGI application.

    It is subclassed from FastAPI with extra methods to handle and translate
    brewing-specific objects.
    """

    app_string_identifier: str
    if not TYPE_CHECKING:

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.app_string_identifier = (
                f"{find_calling_module()}:{self.extra.get('name', 'http')}"
            )

    def include_viewset(self, viewset: ViewSet[Any], **kwargs: Any):
        """
        Add viewset to the application.

        Args:
            viewset (ViewSet): the viewset to be added
            **kwargs (Any): passed directly to FastAPI.include_router

        """
        self.include_router(viewset.router, **kwargs)

    def with_viewsets(self, *vs: ViewSet[Any]) -> Self:
        """
        _summary_.

        Args:
            *vs (ViewSet): viewsets to include

        Returns:
            Self: The BrewingHTTP instance (self)

        """
        for v in vs:
            self.include_viewset(v)
        return self
