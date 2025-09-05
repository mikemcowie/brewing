from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from project_manager import constants, root_router
from project_manager.exceptions import DomainError
from project_manager.organizations.router import router as organizations_router
from project_manager.users.router import router as users_router

if TYPE_CHECKING:
    from starlette.types import ASGIApp


@dataclass
class MountedApp:
    path: str
    app: ASGIApp
    name: str


def default_routers() -> list[APIRouter]:
    return [root_router.router, users_router, organizations_router]


def handle_exception(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        {"detail": exc.detail, "resource": request.url.path},
        status_code=exc.status_code,
    )


def api_factory(
    mounts: list[MountedApp] | None = None,
    routers: list[APIRouter] | None = None,
    **kwargs: Any,
) -> FastAPI:
    api = FastAPI(**kwargs)
    for router in routers or default_routers():
        api.include_router(router)
    for mount in mounts or []:
        api.mount(mount.path, mount.app, mount.name)
    api.add_exception_handler(DomainError, handle_exception)  # type: ignore[arg-type]
    return api


api = api_factory(
    title=constants.TITLE,
    description=constants.DESCRIPION,
    version=constants.API_VERSION,
)

dev_api = api_factory(
    title=constants.TITLE,
    description=constants.DESCRIPION,
    version=constants.API_VERSION,
    routers=default_routers(),
    mounts=[
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
    ],
)
