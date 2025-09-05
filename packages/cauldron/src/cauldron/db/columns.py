from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import MappedColumn, mapped_column


def uuid_primary_key() -> MappedColumn[UUID]:
    return mapped_column(
        pg.UUID,
        default=None,
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )


def created_field() -> MappedColumn[datetime]:
    return mapped_column(
        DateTime(timezone=True), default=None, index=True, server_default=func.now()
    )


def updated_field() -> MappedColumn[datetime]:
    return mapped_column(
        DateTime(timezone=True),
        default=None,
        index=True,
        server_default=func.now(),
        onupdate=func.now(),
    )


def deleted_field() -> MappedColumn[datetime]:
    return mapped_column(
        DateTime(timezone=True), default=None, index=True, nullable=True
    )
