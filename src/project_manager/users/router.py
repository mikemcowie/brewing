from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from project_manager.db import db_session
from project_manager.secret import secret_value
from project_manager.users.auth import InvalidToken, UserAuth
from project_manager.users.models import Token, User, UserRead, UserRegister

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login", auto_error=False)
router = APIRouter(tags=["users"])


async def user_auth(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db_session: Annotated[AsyncSession, Depends(db_session)],
) -> UserAuth:
    return UserAuth(token=token, db_session=db_session)


async def user(auth: Annotated[UserAuth, Depends(user_auth)]) -> User:
    user = await auth.authenticated_user()
    if not user:
        raise InvalidToken("unauthorized")
    return user


@router.get("/users/profile")
async def user_own_profile(user: Annotated[User, Depends(user)]) -> User:
    return user


@router.post("/users/login")
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth: Annotated[UserAuth, Depends(user_auth)],
) -> Token:
    return await auth.login(
        username=form.username, password=secret_value(form.password)
    )


@router.post("/users/register", status_code=status.HTTP_201_CREATED)
async def register(
    user: UserRegister, auth: Annotated[UserAuth, Depends(user_auth)]
) -> UserRead:
    return await auth.create_user(user)
