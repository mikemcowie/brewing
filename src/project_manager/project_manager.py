from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.staticfiles import StaticFiles

from project_manager import root_router
from project_manager.db import Database
from project_manager.organizations.router import router as organizations_router
from project_manager.settings import Settings
from project_manager.users.router import router as users_router

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.types import ASGIApp

    from project_manager.exceptions import DomainError


@dataclass
class MountedApp:
    path: str
    app: ASGIApp
    name: str


@dataclass
class ExceptionHandler[T: BaseException]:
    exception_type: type[T]
    handler: Callable[[Request, T], Response]


def default_routers() -> list[APIRouter]:
    return [root_router.router, users_router, organizations_router]


def handle_exception(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        {"detail": exc.detail, "resource": request.url.path},
        status_code=exc.status_code,
    )


class ProjectManager:
    # ruff: noqa: PLR0913
    default_app_args: ClassVar[dict[str, str]] = {"title": "Project Manager"}
    default_routers = (root_router.router, users_router, organizations_router)
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
        ExceptionHandler(ValueError, handle_exception),
    )

    def __init__(
        self,
        dev: bool,
        settings: Settings | None = None,
        database: Database | None = None,
        mounts: tuple[MountedApp] | None = None,
        routers: tuple[APIRouter] | None = None,
        app_extra_args: dict[str, Any] | None = None,
        exception_handlers: tuple[ExceptionHandler[Any]] | None = None,
    ):
        self.dev = dev
        self.settings = settings or Settings()
        self.database = database or Database(settings=self.settings)
        self.routers = routers or self.default_routers
        default_mounts = (
            self.dev_default_mounts if self.dev else self.prod_default_mounts
        )
        self.mounts = mounts or default_mounts
        self.app_args = self.default_app_args | (app_extra_args or {})
        self.exception_handlers = exception_handlers or self.default_exception_handlers
        self.app = FastAPI(**self.app_args)
        for router in self.routers:
            self.app.include_router(router)
        for mount in self.mounts:
            self.app.mount(mount.path, mount.app, mount.name)
        for handler in self.exception_handlers:
            self.app.add_exception_handler(handler.exception_type, handler.handler)
