from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    registry,
)

from project_manager.db import Base

reg = registry()


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
