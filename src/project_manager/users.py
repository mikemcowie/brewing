from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from project_manager.endpoints import Endpoints

router = APIRouter(tags=["users"])


@router.get(Endpoints.USERS_PROFILE)
def user_own_profile():
    return JSONResponse(
        content={"detail": "authentication required"},
        status_code=status.HTTP_401_UNAUTHORIZED,
    )
