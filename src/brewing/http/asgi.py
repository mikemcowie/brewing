"""
The Brewing ASGI application.

It is a shallow wrapper around fastapi with extra methods to support native features.
"""

from __future__ import annotations

import inspect
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Annotated

import uvicorn
from fastapi import FastAPI
from typer import Option

from brewing.db import testing

if TYPE_CHECKING:
    from collections.abc import Sequence

    from starlette.types import Receive, Scope, Send

    from brewing import Brewing

    from . import ViewSet


def find_calling_module():
    """Inspect the stack frame and return the module that called this."""
    frame = inspect.currentframe()
    while True:
        assert frame
        frame = frame.f_back
        module = inspect.getmodule(frame)
        if not module:
            continue
        mod_name = module.__name__
        if mod_name != __name__:
            return mod_name


@dataclass
class BrewingHTTP:
    """
    The brewing application.

    It is is a facade around a FastAPI instance with extra methods to handle and translate
    brewing-specific objects.
    """

    viewsets: Sequence[ViewSet]
    title: str = "A Brewing API"
    description: str | None = None
    summary: str | None = None
    version: str = "0.1.0"
    openapi_url: str | None = "/openapi.json"
    docs_url: str | None = "/docs"
    redoc_url: str | None = "/redoc"

    def __post_init__(self):
        self._fastapi = FastAPI(**asdict(self))
        for v in self.viewsets:
            self._fastapi.include_router(v.router)
        self.app_string_identifier = (
            f"{find_calling_module()}:{self._fastapi.extra.get('name', 'http')}"
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Call fastapi instance.

        This method allows the brewing HTTP instance itself to act as an
        ASGI application and hence a direct targetf for webserver like uvicorn.
        """
        return await self._fastapi(scope, receive, send)

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
