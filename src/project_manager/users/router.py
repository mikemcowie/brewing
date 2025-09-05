from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from project_manager.db import db_session
from project_manager.endpoints import Endpoints
from project_manager.secrets import secret_value
from project_manager.users.auth import UserAuth
from project_manager.users.models import User
from project_manager.users.schemas import UserRegister

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=Endpoints.USERS_LOGIN, auto_error=False)
router = APIRouter(tags=["users"])


async def user_auth(
    token: Annotated[str, Depends(oauth2_scheme)],
    db_session: Annotated[AsyncSession, Depends(db_session)],
):
    return UserAuth(token=token, db_session=db_session)


async def user(auth: Annotated[UserAuth, Depends(user_auth)]):
    return await auth.token_user()


@router.get(Endpoints.USERS_PROFILE)
async def user_own_profile(user: Annotated[User, Depends(user)]):
    return user


@router.post(Endpoints.USERS_LOGIN)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth: Annotated[UserAuth, Depends(user_auth)],
):
    return await auth.authenticate(
        username=form.username, password=secret_value(form.password)
    )


@router.post(Endpoints.USERS_REGISTER, status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister, auth: Annotated[UserAuth, Depends(user_auth)]):
    return await auth.create_user(user)
