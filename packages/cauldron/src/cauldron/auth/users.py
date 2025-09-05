from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Annotated

from runtime_generic import runtime_generic
from sqlalchemy.ext.asyncio import AsyncSession

from cauldron.auth.exceptions import InvalidToken
from cauldron.auth.models import Token, User, UserRead, UserRegister, UserSession
from cauldron.db.session import (
    db_session,
)
from cauldron.http import APIRouter, Depends, Request, status
from cauldron.http.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

if TYPE_CHECKING:
    from pydantic import SecretStr
    from sqlalchemy.ext.asyncio import AsyncSession


def secret_value(value: str | SecretStr) -> str:
    return value if isinstance(value, str) else value.get_secret_value()


class UserRepo:
    def __init__(self, session: AsyncSession):
        self._session = session


@dataclass
class AuthConfig:
    base_url: str = "/users"


@runtime_generic
class UserService[RepoT: UserRepo, AuthConfigT: AuthConfig]:
    repo_type: type[RepoT]
    auth_config: type[AuthConfigT]

    def __init__(self, session: AsyncSession):
        self._config = self.auth_config()
        self._repo = self.repo_type(session)

    @cached_property
    def oauth_scheme(self):
        return OAuth2PasswordBearer(
            tokenUrl=f"{self._config.base_url}/login", auto_error=False
        )

    async def token(self, request: Request):
        return await self.oauth_scheme(request)

    async def user_from_request(self, request: Request):
        user = await UserSession.authenticated_user(
            self._repo._session, await self.token(request)
        )
        if not user:
            raise InvalidToken("unauthorized")
        return user


async def service(db_session: Annotated[AsyncSession, Depends(db_session)]):
    return UserService[UserRepo, AuthConfig](session=db_session)


router = APIRouter(tags=["users"])


async def user(
    request: Request,
    service: Annotated[UserService[UserRepo, AuthConfig], Depends(service)],
) -> User:
    return await service.user_from_request(request)


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
