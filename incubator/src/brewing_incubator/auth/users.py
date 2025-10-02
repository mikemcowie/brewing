from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cached_property
from secrets import token_bytes
from typing import TYPE_CHECKING, Annotated

from brewing.generic import runtime_generic
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from brewing_incubator.auth.exceptions import InvalidToken
from brewing_incubator.auth.models import (
    Token,
    User,
    UserRead,
    UserRegister,
    UserSession,
)
from brewing_incubator.auth.repo import UserRepo
from brewing_incubator.db.session import (
    db_session,
)
from brewing_incubator.exceptions import Unauthorized
from brewing_incubator.http import Depends, Request, status
from brewing_incubator.http.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
from brewing_incubator.http.viewset import Endpoint, ViewSet

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12
TOKEN_BYTES = 48


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
        self._password_context = CryptContext(schemes=["argon2"], deprecated="auto")

    @cached_property
    def oauth_scheme(self):
        return OAuth2PasswordBearer(
            tokenUrl=f"{self._config.base_url}/login", auto_error=False
        )

    async def token(self, request: Request):
        return await self.oauth_scheme(request)

    async def user_from_request(self, request: Request):
        token = await self.token(request)
        if not token:
            raise Unauthorized("unauthorized")
        user_session = await self._repo.validated(
            hashlib.sha512(token.encode()).hexdigest()
        )
        if not user_session:
            raise InvalidToken("unauthorized")
        return user_session.user

    async def authorize(self, form: OAuth2PasswordRequestForm):
        username, password = form.username, form.password
        user = await self._repo.user_from_email(username)
        if (
            user is None
            or not user.password_hash
            or not self._password_context.verify(password, user.password_hash)
        ):
            raise Unauthorized("incorrect username or password")
        # password has been validated, so from here we are just constrcting a user session,
        # flushing to the database, and returning the token
        token = base64.b64encode(token_bytes(TOKEN_BYTES)).decode()
        await self._repo.add(
            UserSession(
                id=hashlib.sha512(token.encode()).hexdigest(),
                user=user,
                expires=datetime.now(UTC) + timedelta(ACCESS_TOKEN_EXPIRE_MINUTES),
            )
        )
        await self._repo.commit()
        return Token(access_token=token)

    async def register(self, new_user: UserRegister):
        user = User(**new_user.model_dump())
        user.password_hash = self._password_context.hash(user.password)
        user.password = ""  # forget the actual password.
        await self._repo.add(user)
        await self._repo.commit()
        return UserRead.model_validate(user, from_attributes=True)


async def service(db_session: Annotated[AsyncSession, Depends(db_session)]):
    return UserService[UserRepo, AuthConfig](session=db_session)


async def user(
    request: Request,
    service: Annotated[UserService[UserRepo, AuthConfig], Depends(service)],
) -> User:
    return await service.user_from_request(request)


class UserViewSet(ViewSet):
    tags = ("users",)
    dependencies = ()
    base_path = ("users",)

    users_endpoint = Endpoint(trailing_slash=True)
    profile_endpoint = users_endpoint.action("profile")
    login_endpoint = users_endpoint.action("login")
    register_endpoint = users_endpoint.action("register")

    @profile_endpoint.GET()
    async def user_own_profile(self, user: Annotated[User, Depends(user)]) -> User:
        return user

    @login_endpoint.POST()
    async def login(
        self,
        form: Annotated[OAuth2PasswordRequestForm, Depends()],
        service: Annotated[UserService[UserRepo, AuthConfig], Depends(service)],
    ) -> Token:
        return await service.authorize(form)

    @register_endpoint.POST(status_code=status.HTTP_201_CREATED)
    async def register(
        self,
        user: UserRegister,
        service: Annotated[UserService[UserRepo, AuthConfig], Depends(service)],
    ) -> UserRead:
        return await service.register(user)


router = UserViewSet().router
