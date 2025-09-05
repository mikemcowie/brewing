from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from sqlalchemy.ext.asyncio import AsyncSession

from cauldron.auth.exceptions import InvalidToken
from cauldron.auth.models import Token, User, UserRead, UserRegister, UserSession
from cauldron.db.session import (
    db_session,
)
from cauldron.http import APIRouter, Depends, status
from cauldron.http.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

if TYPE_CHECKING:
    from pydantic import SecretStr
    from sqlalchemy.ext.asyncio import AsyncSession


def secret_value(value: str | SecretStr) -> str:
    return value if isinstance(value, str) else value.get_secret_value()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login", auto_error=False)
router = APIRouter(tags=["users"])


async def user(
    db_session: Annotated[AsyncSession, Depends(db_session)],
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    user = await UserSession.authenticated_user(db_session, token)
    if not user:
        raise InvalidToken("unauthorized")
    return user


@router.get("/users/profile")
async def user_own_profile(user: Annotated[User, Depends(user)]) -> User:
    return user


@router.post("/users/login")
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db_session: Annotated[AsyncSession, Depends(db_session)],
) -> Token:
    return await User.authorize(
        db_session, email=form.username, password=secret_value(form.password)
    )


@router.post("/users/register", status_code=status.HTTP_201_CREATED)
async def register(
    user: UserRegister,
    db_session: Annotated[AsyncSession, Depends(db_session)],
) -> UserRead:
    return UserRead.model_validate(
        await User.create_user(db_session, user), from_attributes=True
    )
