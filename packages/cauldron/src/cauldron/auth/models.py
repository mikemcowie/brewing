from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    MappedColumn,
    mapped_column,
    relationship,
)

from cauldron.db.base import Base
from cauldron.db.columns import created_field, updated_field, uuid_primary_key

UUID = uuid.UUID


class User(MappedAsDataclass, Base, kw_only=True):
    id: Mapped[UUID] = uuid_primary_key()
    email: Mapped[str] = mapped_column(index=True)
    password_hash: Mapped[str] = mapped_column(default="")
    password: str = ""  # unmapped attribute that will be turned into the password hash
    created: Mapped[datetime] = created_field()
    updated: Mapped[datetime] = created_field()

    @staticmethod
    def primary_foreign_key_to(*, init: bool) -> MappedColumn[UUID]:
        return mapped_column(ForeignKey("user.id"), primary_key=True, init=init)

    @property
    def username(self) -> str:
        """Username is an alias for email."""
        return self.email


class UserSession(MappedAsDataclass, Base, kw_only=True):
    id: Mapped[str] = mapped_column(primary_key=True)
    created: Mapped[datetime] = created_field()
    updated: Mapped[datetime] = updated_field()
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[UUID] = mapped_column(ForeignKey(User.id), init=False)
    user: Mapped[User] = relationship(lazy="joined")

    def __post_init__(self):
        self.encrypted_token = b""


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: UUID
    username: str
