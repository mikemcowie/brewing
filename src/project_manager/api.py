from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from project_manager import constants, root_router
from project_manager.users.auth import DomainError
from project_manager.users.router import router as users_router


def default_routers():
    return [root_router.router, users_router]


def handle_exception(request: Request, exc: DomainError):
    return JSONResponse(
        {"detail": exc.detail, "resource": request.url.path},
        status_code=exc.status_code,
    )


def api_factory(routers: list[APIRouter] | None = None, **kwargs: Any):
    api = FastAPI(**kwargs)
    for router in routers or default_routers():
        api.include_router(router)
    api.add_exception_handler(DomainError, handle_exception)  # type: ignore[arg-type]
    return api


api = api_factory(
    title=constants.TITLE,
    description=constants.DESCRIPION,
    version=constants.API_VERSION,
)
