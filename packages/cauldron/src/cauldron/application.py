from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from runtime_generic import runtime_generic
from starlette.staticfiles import StaticFiles

from cauldron import root_router
from cauldron.configuration import BaseConfiguration
from cauldron.db import Database
from cauldron.exceptions import DomainError
from cauldron.logging import setup_logging
from cauldron.settings import Settings
from cauldron.users import router as users_router

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from starlette.types import ASGIApp


@dataclass
class MountedApp:
    path: str
    app: ASGIApp
    name: str


@dataclass
class ExceptionHandler[T: BaseException]:
    exception_type: type[T]
    handler: Callable[[Request, T], Response]


def handle_exception(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        {"detail": exc.detail, "resource": request.url.path},
        status_code=exc.status_code,
    )


@runtime_generic
class Application[ConfigT: BaseConfiguration]:
    config_type: type[ConfigT]
    default_routers = (
        root_router.router,
        users_router,
    )
    prod_default_mounts: tuple[MountedApp, ...] = ()
    dev_default_mounts: tuple[MountedApp, ...] = (
        MountedApp(
            path="/htmlcov",
            app=StaticFiles(
                directory=Path(__file__).parents[2] / "htmlcov",
                html=True,
                check_dir=False,
            ),
            name="htmlcov",
        ),
        MountedApp(
            path="/testreport",
            app=StaticFiles(
                directory=Path(__file__).parents[2] / "testreport",
                html=True,
                check_dir=False,
            ),
            name="testreport",
        ),
    )
    default_exception_handlers: tuple[ExceptionHandler[Any]] = (
        ExceptionHandler(DomainError, handle_exception),
    )

    def __init__(
        self,
        routers: Sequence[APIRouter],
        settings: Settings | None = None,
        database: Database | None = None,
        exception_handlers: tuple[ExceptionHandler[Any]] | None = None,
    ):
        setup_logging()
        self.config = self.config_type()
        self.settings = settings or Settings()
        self.database = database or Database(settings=self.settings)
        self.routers = tuple(routers) + self.default_routers
        self.exception_handlers = exception_handlers or self.default_exception_handlers

    def _create_app(self, dev: bool):
        mounts = self.dev_default_mounts if dev else self.prod_default_mounts
        app = FastAPI(
            title=self.config.title,
            version=self.config.version,
            description=self.config.description,
        )
        app.project_manager = self  # type: ignore
        for router in self.routers:
            app.include_router(router)
        for mount in mounts:
            app.mount(mount.path, mount.app, mount.name)
        for handler in self.exception_handlers:
            app.add_exception_handler(handler.exception_type, handler.handler)
        return app

    @cached_property
    def dev_app(self):
        return self._create_app(dev=True)

    @cached_property
    def app(self):
        return self._create_app(dev=False)
