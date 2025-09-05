from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime, timedelta
from functools import cache
from secrets import token_bytes
from typing import TYPE_CHECKING, Annotated, Literal
from uuid import UUID  # noqa

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, SecretStr
from sqlalchemy import DateTime, ForeignKey, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    MappedColumn,
    mapped_column,
    relationship,
)

from cauldron.db import (
    Base,
    created_field,
    db_session,
    updated_field,
    uuid_primary_key,
)
from cauldron.exceptions import DomainError, Unauthorized

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12
TOKEN_BYTES = 48


def secret_value(value: str | SecretStr) -> str:
    return value if isinstance(value, str) else value.get_secret_value()


@cache
def password_context() -> CryptContext:
    return CryptContext(schemes=["argon2"], deprecated="auto")


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class User(MappedAsDataclass, Base, kw_only=True):
    id: Mapped[UUID] = uuid_primary_key()
    email: Mapped[str] = mapped_column(index=True)
    password_hash: Mapped[str] = mapped_column(default="")
    password: str = ""  # unmapped attribute that will be turned into the password hash
    created: Mapped[datetime] = created_field()
    updated: Mapped[datetime] = created_field()

    def __post_init__(self):
        if self.password:
            self.password_hash = password_context().hash(self.password)
            self.password = ""  # forget the actual password.

    @staticmethod
    def primary_foreign_key_to(*, init: bool) -> MappedColumn[UUID]:
        return mapped_column(ForeignKey("user.id"), primary_key=True, init=init)

    @property
    def username(self) -> str:
        """Username is an alias for email."""
        return self.email

    @classmethod
    async def authorize(cls, session: AsyncSession, email: str, password: str) -> Token:
        user = (
            await session.execute(select(cls).where(cls.email == email))
        ).scalar_one_or_none()
        if (
            user is None
            or not user.password_hash
            or not password_context().verify(password, user.password_hash)
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
        session.add(user_session)
        session.add(user)
        await session.flush()
        await session.commit()
        return Token(access_token=token)

    @classmethod
    async def create_user(cls, session: AsyncSession, user: UserRegister) -> UserRead:
        async with session.begin():
            db_user = User(**user.model_dump())
            session.add(db_user)
            await session.flush()
            return UserRead.model_validate(db_user, from_attributes=True)


class UserSession(MappedAsDataclass, Base, kw_only=True):
    id: Mapped[str] = mapped_column(primary_key=True)
    created: Mapped[datetime] = created_field()
    updated: Mapped[datetime] = updated_field()
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[UUID] = mapped_column(ForeignKey(User.id), init=False)
    user: Mapped[User] = relationship(lazy="joined")

    def __post_init__(self):
        self.encrypted_token = b""

    @classmethod
    async def validated(cls, token: str, session: AsyncSession) -> UserSession | None:
        user_session = (
            await session.execute(
                select(cls)
                .where(cls.id == hashlib.sha512(token.encode()).hexdigest())
                .where(cls.expires > datetime.now(UTC))
            )
        ).scalar_one_or_none()
        if not user_session:
            return None
        return user_session

    @classmethod
    async def authenticated_user(
        cls, session: AsyncSession, token: str | None
    ) -> User | None:
        if not token:
            return None
        if user_session := await cls.validated(token, session):
            return user_session.user
        raise InvalidToken(detail="invalid token")


class UserRead(BaseModel):
    id: UUID
    username: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str


class LoginFailure(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "incorrect username or password"


class InvalidToken(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "invalid token."


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
    return await User.create_user(db_session, user)
