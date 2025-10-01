"""Helper functions to provide common or reusable column types."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import mysql, sqlite
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import (
    mapped_column,
)

json_column_type = (
    sa.JSON()
    .with_variant(pg.JSONB, "postgresql")
    .with_variant(sqlite.JSON, "sqlite")
    .with_variant(mysql.JSON, "mysql", "mariadb")
)
uuid_column_type = (
    sa.UUID().with_variant(pg.UUID, "postgresql").with_variant(sa.String(36), "mysql")
)
type NewUUIDFactory = Callable[[], uuid.UUID] | sa.Function[Any]


# on python 3.14, client-generateduuid7 will be the default
# older versions, client-generated uuid4 will be default
try:
    uuid_default_provider = uuid.uuid7  # type: ignore
except AttributeError:
    uuid_default_provider = uuid.uuid4


def uuid_primary_key(uuid_provider: NewUUIDFactory = uuid_default_provider):
    """
    UUID primary key column.

    If the provider given is an sqlalchemy function, a server default will be provided
    otherwise a sqlalchemy/python-generated value will be provided.
    """
    if isinstance(uuid_provider, sa.Function):
        return mapped_column(
            uuid_column_type, primary_key=True, server_default=uuid_provider, init=False
        )  # type: ignore
    else:
        return mapped_column(
            uuid_column_type,
            primary_key=True,
            default_factory=uuid_provider,
            init=False,
        )


def created_at_column(**kwargs: Any):
    """Column that stores the datetime that the record was created."""
    return mapped_column(
        sa.DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        init=False,
        **kwargs,
    )


def updated_at_column():
    """Column that stores the datetime that the record was last updated."""
    return created_at_column(onupdate=lambda: datetime.now(UTC))
