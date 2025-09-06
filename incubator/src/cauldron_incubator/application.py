from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cauldronlib.generic import runtime_generic
from starlette.staticfiles import StaticFiles

from cauldron_incubator import root_router
from cauldron_incubator.auth.users import router as users_router
from cauldron_incubator.configuration import BaseConfiguration
from cauldron_incubator.db.database import Database
from cauldron_incubator.db.settings import PostgresqlSettings
from cauldron_incubator.exceptions import DomainError
from cauldron_incubator.http import APIRouter, CauldronHTTP, Request
from cauldron_incubator.http.responses import JSONResponse, Response
from cauldron_incubator.logging import setup_logging

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from starlette.types import ASGIApp

    from cauldron_incubator.http.viewset import AbstractViewSet


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
                directory=Path(__file__).parents[3] / "htmlcov",
                html=True,
                check_dir=False,
            ),
            name="htmlcov",
        ),
        MountedApp(
            path="/testreport",
            app=StaticFiles(
                directory=Path(__file__).parents[3] / "testreport",
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
        viewsets: Sequence[AbstractViewSet | APIRouter],
        exception_handlers: tuple[ExceptionHandler[Any]] | None = None,
    ):
        setup_logging()
        self.config = self.config_type()
        self._database = Database[PostgresqlSettings]()
        self.exception_handlers = exception_handlers or self.default_exception_handlers
        self.viewsets = viewsets

    def _create_app(self, dev: bool):
        mounts = self.dev_default_mounts if dev else self.prod_default_mounts
        app = CauldronHTTP(
            title=self.config.title,
            version=self.config.version,
            description=self.config.description,
        )
        app.project_manager = self  # type: ignore
        for viewset in list(self.default_routers) + list(self.viewsets):
            app.include_router(viewset) if isinstance(
                viewset, APIRouter
            ) else app.include_viewset(viewset)
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

    @cached_property
    def database(self):
        return self._database
