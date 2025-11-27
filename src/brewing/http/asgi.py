"""
The Brewing ASGI application.

It is a shallow wrapper around fastapi with extra methods to support native features.
"""

from __future__ import annotations

import inspect
from dataclasses import asdict, dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Annotated

import uvicorn
from fastapi import FastAPI
from typer import Option

from brewing.context import current_app
from brewing.db import testing
from brewing.serialization import ExcludeCachedProperty

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


def _app_factory():
    current_component = current_app().current_component
    if not isinstance(current_component, BrewingHTTP):
        raise TypeError("Current component has not been set to a BrewingHTTP instance")
    return current_component.fastapi


_APP_FACTORY_NAME = f"{__name__}:{_app_factory.__name__}"


@dataclass
class BrewingHTTP(ExcludeCachedProperty):
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

    @cached_property
    def fastapi(self) -> FastAPI:
        """Return fastapi instance associated with the HTTP class."""
        app = FastAPI(**asdict(self))
        for v in self.viewsets:
            v.__post_init__()
            app.include_router(v.router)
        return app

    def __getstate__(self):
        """Override the attributes dumped when the object is pickled.

        This is used to bypass pickling the fastapi instance, which instead
        will be recreated as a cached property on first call after unpicking,
        """
        state = self.__dict__.copy()
        state.pop("fastapi", None)
        return state

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Call fastapi instance.

        This method allows the brewing HTTP instance itself to act as an
        ASGI application and hence a direct targetf for webserver like uvicorn.
        """
        return await self.fastapi(scope, receive, send)

    def register(self, name: str, brewing: Brewing, /):
        """Register http server to brewing."""
        brewing.current_component = self

        @brewing.cli.typer.command(name)
        def run(
            dev: Annotated[bool, Option()] = False,
            workers: None | int = None,
            host: str = "0.0.0.0",
            port: int = 8000,
        ):
            """Run the HTTP server."""
            with brewing:
                if dev:
                    with testing.dev(brewing.database.database_type):
                        return uvicorn.run(
                            _APP_FACTORY_NAME,
                            host=host,
                            port=port,
                            reload=dev,
                            factory=True,
                        )
                return uvicorn.run(
                    _APP_FACTORY_NAME,
                    host=host,
                    workers=workers,
                    port=port,
                    reload=False,
                    factory=True,
                )
