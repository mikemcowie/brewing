from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    registry,
)

from project_manager.db import Base, created_field, uuid_primary_key

reg = registry()


class User(MappedAsDataclass, Base, kw_only=True):
    id: Mapped[UUID] = uuid_primary_key()
    email: Mapped[str] = mapped_column(index=True)
    password_hash: Mapped[str]
    created: Mapped[datetime] = created_field()
    updated: Mapped[datetime] = created_field()

    @property
    def username(self) -> str:
        """Username is an alias for email."""
        return self.email
