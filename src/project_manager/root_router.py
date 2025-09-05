from typing import TYPE_CHECKING

from fastapi import APIRouter, FastAPI, Request
from pydantic import BaseModel

from project_manager._version import version

router = APIRouter(tags=["root"])


class APIRootResponse(BaseModel):
    title: str
    description: str
    deployed_version: str
    api_version: str


@router.get("/", response_model=APIRootResponse)
async def api_root(request: Request):
    app = request.app
    if TYPE_CHECKING:
        assert isinstance(app, FastAPI)
    return APIRootResponse(
        title=app.title,
        description=app.description,
        deployed_version=version,
        api_version=app.version,
    )
