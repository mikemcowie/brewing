from typing import Any

from fastapi import APIRouter, FastAPI

from project_manager import root_router


def default_routers():
    return [root_router.router]


def api_factory(routers: list[APIRouter] | None = None, **kwargs: Any):
    api = FastAPI(**kwargs)
    for router in routers or default_routers():
        api.include_router(router)
    return api


api = api_factory()
