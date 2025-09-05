from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cached_property
from secrets import token_bytes
from typing import TYPE_CHECKING, Annotated

from passlib.context import CryptContext
from runtime_generic import runtime_generic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cauldron.auth.exceptions import InvalidToken
from cauldron.auth.models import Token, User, UserRead, UserRegister, UserSession
from cauldron.db.session import (
    db_session,
)
from cauldron.exceptions import Unauthorized
from cauldron.http import APIRouter, Depends, Request, status
from cauldron.http.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12
TOKEN_BYTES = 48


class UserRepo:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._password_context = CryptContext(schemes=["argon2"], deprecated="auto")

    async def validated(self, token: str) -> UserSession | None:
        user_session = (
            await self._session.execute(
                select(UserSession)
                .where(UserSession.id == hashlib.sha512(token.encode()).hexdigest())
                .where(UserSession.expires > datetime.now(UTC))
            )
        ).scalar_one_or_none()
        if not user_session:
            return None
        return user_session

    async def authenticated_user(self, token: str | None) -> User | None:
        if not token:
            return None
        if user_session := await self.validated(token):
            return user_session.user
        raise InvalidToken(detail="invalid token")

    async def authorize(self, username: str, password: str):
        user = (
            await self._session.execute(select(User).where(User.email == username))
        ).scalar_one_or_none()
        if (
            user is None
            or not user.password_hash
            or not self._password_context.verify(password, user.password_hash)
        ):
            raise Unauthorized("incorrect username or password")
        # password has been validated, so from here we are just constrcting a user session,
        # flushing to the database, and returning the token
        token = base64.b64encode(token_bytes(TOKEN_BYTES)).decode()
        user_session = UserSession(
            id=hashlib.sha512(token.encode()).hexdigest(),
            user=user,
            expires=datetime.now(UTC) + timedelta(ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        self._session.add(user_session)
        self._session.add(user)
        await self._session.flush()
        await self._session.commit()
        return Token(access_token=token)

    async def create_user(self, new_user: UserRegister) -> User:
        async with self._session.begin():
            user = User(**new_user.model_dump())
            user.password_hash = self._password_context.hash(user.password)
            user.password = ""  # forget the actual password.
            self._session.add(user)
            await self._session.flush()
            return user


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
        user = await self._repo.authenticated_user(await self.token(request))
        if not user:
            raise InvalidToken("unauthorized")
        return user

    async def authorize(self, form: OAuth2PasswordRequestForm):
        return await self._repo.authorize(
            username=form.username, password=form.password
        )

    async def register(self, user: UserRegister):
        return UserRead.model_validate(
            await self._repo.create_user(user), from_attributes=True
        )


async def service(db_session: Annotated[AsyncSession, Depends(db_session)]):
    return UserService[UserRepo, AuthConfig](session=db_session)


async def user(
    request: Request,
    service: Annotated[UserService[UserRepo, AuthConfig], Depends(service)],
) -> User:
    return await service.user_from_request(request)


class UserViewSet:
    def __init__(self):
        self._router = APIRouter(tags=["users"])
        self.setup_endpoints()

    @property
    def router(self):
        return self._router

    def setup_endpoints(self):
        @self.router.get("/users/profile")
        async def user_own_profile(user: Annotated[User, Depends(user)]) -> User:
            return user

        @self.router.post("/users/login")
        async def login(
            form: Annotated[OAuth2PasswordRequestForm, Depends()],
            service: Annotated[UserService[UserRepo, AuthConfig], Depends(service)],
        ) -> Token:
            return await service.authorize(form)

        @self.router.post("/users/register", status_code=status.HTTP_201_CREATED)
        async def register(
            user: UserRegister,
            service: Annotated[UserService[UserRepo, AuthConfig], Depends(service)],
        ) -> UserRead:
            return await service.register(user)


router = UserViewSet().router
