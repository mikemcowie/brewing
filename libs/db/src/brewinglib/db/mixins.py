"""Mixin classes that can be applied to help constuct declartive mapped classes"""

import uuid
from datetime import datetime

from brewinglib.db import columns
from sqlalchemy import orm


class AuditMixin(orm.MappedAsDataclass):
    @orm.declared_attr
    def created_at(self) -> orm.Mapped[datetime]:
        return columns.created_at_column()

    @orm.declared_attr
    def updated_at(self) -> orm.Mapped[datetime]:
        return columns.updated_at_column()


class UUIDPrimaryKey(orm.MappedAsDataclass, kw_only=True):
    id: orm.Mapped[uuid.UUID] = columns.uuid_primary_key()


class IncrementingIntPK(orm.MappedAsDataclass):
    __abstract__ = True
    id: orm.Mapped[int] = orm.mapped_column(
        primary_key=True, autoincrement=True, init=False
    )
