from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from cauldron_incubator.http import APIRouter, CauldronHTTP, Request

router = APIRouter(tags=["root"])


class APIRootResponse(BaseModel):
    title: str
    description: str
    api_version: str


@router.get("/", response_model=APIRootResponse)
async def api_root(request: Request) -> APIRootResponse:
    app = request.app
    if TYPE_CHECKING:
        assert isinstance(app, CauldronHTTP)
    return APIRootResponse(
        title=app.title,
        description=app.description,
        api_version=app.version,
    )
