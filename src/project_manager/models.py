from datetime import datetime
from uuid import UUID

from pydantic.alias_generators import to_snake
from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    declared_attr,
    mapped_column,
    registry,
)

from project_manager.db import Database

reg = registry()


class Base(DeclarativeBase):
    __abstract__ = True
    metadata = Database.metadata

    @declared_attr  # type: ignore
    def __tablename__(cls) -> str:  # noqa: N805
        return to_snake(cls.__name__)


def uuid_primary_key():
    return mapped_column(
        pg.UUID,
        default=None,
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )


def created_field():
    return mapped_column(DateTime, default=None, index=True, server_default=func.now())


def updated_field():
    return mapped_column(
        DateTime,
        default=None,
        index=True,
        server_default=func.now(),
        onupdate=func.now(),
    )


class User(MappedAsDataclass, Base, kw_only=True):
    id: Mapped[UUID] = uuid_primary_key()
    email: Mapped[str] = mapped_column(index=True)
    password_hash: Mapped[str]
    created: Mapped[datetime] = created_field()
    updated: Mapped[datetime] = created_field()

    @property
    def username(self):
        """Username is an alias for email."""
        return self.email
