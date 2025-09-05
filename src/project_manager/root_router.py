from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["root"])


@router.get("/")
def api_root(request: Request):
    return JSONResponse({"title": request.app.title})
