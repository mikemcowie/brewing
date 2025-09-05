from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum, auto
from functools import cache
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, create_model
from sqlalchemy import ForeignKey, event
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    MappedColumn,
    declared_attr,
    mapped_column,
    relationship,
)

from project_manager import db
from project_manager.users.models import User

TypeBaseModel = type[BaseModel]


class ReadModelType(BaseModel):
    id: UUID
    created: datetime
    updated: datetime


class SummaryModelType(BaseModel):
    id: UUID


@dataclass
class ResourceSchemas:
    create: type[BaseModel]
    summary: type[SummaryModelType]
    read: type[ReadModelType]
    update: type[BaseModel]


class AccessLevel(StrEnum):
    owner = auto()
    contributor = auto()
    reader = auto()


class Resource(MappedAsDataclass, db.Base, kw_only=True):
    read_only_fields: ClassVar[tuple[str, ...]] = ("id", "created", "updated", "type")
    summary_fields: ClassVar[tuple[str, ...]] = ("id", "type")
    id: Mapped[UUID] = db.uuid_primary_key()
    created: Mapped[datetime] = db.created_field()
    updated: Mapped[datetime] = db.updated_field()
    type: Mapped[str] = mapped_column(index=True, init=False)
    deleted: Mapped[datetime | None] = db.deleted_field()

    @declared_attr  # type: ignore
    def __mapper_args__(cls) -> dict[str, str]:  # noqa: N805
        retval: dict[str, str] = {"polymorphic_identity": cls.__tablename__}
        if cls.__name__ == "Resource":
            retval["polymorphic_on"] = "type"
        return retval

    @classmethod
    def create_new_model(
        cls,
        name: str,
        excluded: Iterable[str] | None = None,
        included: Iterable[str] | None = None,
    ) -> TypeBaseModel:
        included = list(included) if included is not None else included
        included = included or list(cls.__annotations__.keys())
        excluded = excluded or []
        return create_model(
            name,
            __config__=ConfigDict(extra="forbid"),
            **{
                attr: (cls.__dict__[attr].type.python_type)
                for attr in cls.__dataclass_fields__
                if all([attr not in excluded, attr in included])
            },
        )

    @classmethod
    @cache
    def schemas(cls) -> ResourceSchemas:
        read = (
            ReadModelType
            if TYPE_CHECKING
            else cls.create_new_model(
                f"Read{cls.__name__}",
                included=cls.summary_fields + cls.read_only_fields,
            )
        )
        summary = (
            SummaryModelType
            if TYPE_CHECKING
            else cls.create_new_model(
                f"Summary{cls.__name__}", included=cls.summary_fields
            )
        )
        create = (
            BaseModel
            if TYPE_CHECKING
            else cls.create_new_model(
                f"Create{cls.__name__}", excluded=cls.read_only_fields
            )
        )
        update = (
            BaseModel
            if TYPE_CHECKING
            else cls.create_new_model(
                f"Update{cls.__name__}", excluded=cls.read_only_fields
            )
        )
        return ResourceSchemas(
            create=create,
            summary=summary,  # type: ignore[arg-type]
            read=read,  # type: ignore[arg-type]
            update=update,
        )

    @staticmethod
    def primary_foreign_key_to(*, init: bool) -> MappedColumn[UUID]:
        return mapped_column(ForeignKey("resource.id"), primary_key=True, init=init)


class ResourceAccess(MappedAsDataclass, db.Base, kw_only=True):
    resource_id: Mapped[UUID] = Resource.primary_foreign_key_to(init=True)
    user_id: Mapped[UUID] = User.primary_foreign_key_to(init=True)
    access: Mapped[AccessLevel]
    resource: Mapped[Resource] = relationship(lazy="joined", init=False)
    user: Mapped[User] = relationship(lazy="joined", init=False)


class ResourceAccessItem(BaseModel):
    principal_id: UUID = Field(default=..., alias="user_id")
    access: AccessLevel


def update_modified_on_update_listener(_: Any, __: Any, target: Resource) -> None:
    """Event listener that runs before a record is updated, and sets the modified field accordingly."""
    # it's okay if this field doesn't exist - SQLAlchemy will silently ignore it.
    target.updated = datetime.now(tz=UTC)


# This actually makes the updated field work.
event.listen(
    Resource, "before_update", update_modified_on_update_listener, propagate=True
)
