"""
The Brewing ASGI application.

It is a shallow wrapper around fastapi with extra methods to support native features.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any
from fastapi import FastAPI

if TYPE_CHECKING:
    from . import ViewSet


class BrewingHTTP(FastAPI):
    """
    The brewing ASGI application.

    It is subclassed from FastAPI with extra methods to handle and translate
    brewing-specific objects.
    """

    def include_viewset(self, viewset: ViewSet, **kwargs: Any):
        """
        Add viewset to the application.

        Args:
            viewset (ViewSet): the viewset to be added
            **kwargs (Any): passed directly to FastAPI.include_router

        """
        self.include_router(viewset.router, **kwargs)
