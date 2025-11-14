"""
The Brewing ASGI application.

It is a shallow wrapper around fastapi with extra methods to support native features.
"""

from __future__ import annotations
import inspect
from typing import TYPE_CHECKING, Any, Self, Annotated
from typer import Option
from fastapi import FastAPI
import uvicorn
from brewing.db import testing


if TYPE_CHECKING:
    from . import ViewSet
    from brewing import Brewing


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

    def register(self, name: str, brewing: Brewing, /):
        """Register http server to brewing."""

        @brewing.cli.typer.command(name)
        def run(
            dev: Annotated[bool, Option()] = False,
            workers: None | int = None,
            host: str = "0.0.0.0",
            port: int = 8000,
        ):
            """Run the HTTP server."""
            if dev:
                with testing.dev(brewing.database.database_type):
                    return uvicorn.run(
                        self.app_string_identifier,
                        host=host,
                        port=port,
                        reload=dev,
                    )
            return uvicorn.run(
                self.app_string_identifier,
                host=host,
                workers=workers,
                port=port,
                reload=False,
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
