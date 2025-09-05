from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from functools import cache
from secrets import token_bytes
from typing import TYPE_CHECKING, Literal
from uuid import UUID  # noqa

from cryptography.fernet import Fernet
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

from project_manager.db import Base, created_field, updated_field, uuid_primary_key
from project_manager.exceptions import Unauthorized

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from project_manager.settings import Settings

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12
TOKEN_BYTES = 48


@cache
def password_context() -> CryptContext:
    return CryptContext(schemes=["argon2"], deprecated="auto")


@cache
def fernet(settings: Settings):
    return Fernet(settings.SECRET_KEY.get_secret_value())


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
            raise Unauthorized()
        # password has been validated, so from here we are just constrcting a user session,
        # flushing to the database, and returning the token
        user_session = UserSession(
            user=user,
            expires=datetime.now(UTC) + timedelta(ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        session.add(user_session)
        session.add(user)
        await session.flush()
        token = token_bytes(TOKEN_BYTES)
        user_session.set_token(token)
        return Token(access_token=base64.b64encode(token).decode())


class UserSession(MappedAsDataclass, Base, kw_only=True):
    id: Mapped[UUID] = uuid_primary_key()
    encrypted_token: Mapped[bytes] = mapped_column(init=False)
    created: Mapped[datetime] = created_field()
    updated: Mapped[datetime] = updated_field()
    expires: Mapped[datetime] = mapped_column()
    user_id: Mapped[UUID] = mapped_column(ForeignKey(User.id), init=False)
    user: Mapped[User] = relationship()

    def __post_init__(self):
        self.encrypted_token = b""

    def set_token(self, token: bytes) -> str:
        self.encrypted_token = fernet().encrypt(token)
        return f"{self.id!s}:{base64.b64encode(token).decode()}"

    def check_token(self, token: Token):
        return (
            fernet().encrypt(base64.b64decode(token.access_token.split(":")[1]))
            == self.encrypted_token
        )

    @classmethod
    async def validate_token(cls, token: Token, session: AsyncSession) -> bool:
        token_id = token.access_token.split(":")[0]
        user_session = (
            await session.execute(
                select(cls)
                .where(cls.id == token_id)
                .where(cls.expires > datetime.now(UTC))
            )
        ).scalar_one_or_none()
        if not user_session or not user_session.encrypted_token:
            return False
        return user_session.check_token(token)
