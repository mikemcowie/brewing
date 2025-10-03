"""Mixin classes that can be applied to help constuct declartive mapped classes."""

import uuid
import warnings
from datetime import datetime

from brewing.db import columns
from sqlalchemy import orm


class AuditMixin(orm.MappedAsDataclass):
    """Mixin to add created_at and updated_at columns to a table."""

    @orm.declared_attr
    def created_at(self) -> orm.Mapped[datetime]:
        """Column set to the original time the record was created."""
        return columns.created_at_column()

    @orm.declared_attr
    def updated_at(self) -> orm.Mapped[datetime]:
        """Column that is updated whenever an update is issued against an instance of class."""
        return columns.updated_at_column()


# per https://github.com/sqlalchemy/sqlalchemy/issues/6320
# warning raised here can be ignored.
warnings.filterwarnings(
    "ignore", message=".*Unmanaged access of declarative attribute.*"
)


class UUIDPrimaryKey(orm.MappedAsDataclass, kw_only=True):
    """Mixin to use a python-generated UUID primary key."""

    id: orm.Mapped[uuid.UUID] = columns.uuid_primary_key()


class IncrementingIntPK(orm.MappedAsDataclass):
    """Mixin to use an incrementing integer as primary key."""

    __abstract__ = True
    id: orm.Mapped[int] = orm.mapped_column(
        primary_key=True, autoincrement=True, init=False
    )
