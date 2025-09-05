from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum, auto
from functools import cache
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, create_model
from sqlalchemy import ForeignKey, event
from sqlalchemy.orm import (
    InstrumentedAttribute,
    Mapped,
    MappedAsDataclass,
    MappedColumn,
    declared_attr,
    mapped_column,
    relationship,
)

from cauldron.auth.models import User
from cauldron.db import base, columns
from cauldron.db.base import Base

if TYPE_CHECKING:
    from collections.abc import Iterable

UUID = uuid.UUID
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

    def is_owner(self):
        return self == self.__class__.owner

    def is_contributor(self):
        return self.is_owner() or self == self.__class__.contributor

    def is_reader(self):
        return self.is_contributor() or self == self.__class__.reader


@dataclass
class ResourceAttributes:
    """Attributes for the resource model.

    Implemtned as a separate class so inheritence can be used to create test versions
    of the Resource class with different metada.
    """

    __tablename__: ClassVar[str]
    __dataclass_fields__: ClassVar[list[str]]
    plural_name: ClassVar[str]
    singular_name: ClassVar[str]
    read_only_fields: ClassVar[tuple[str, ...]] = ("id", "created", "updated", "type")
    summary_fields: ClassVar[tuple[str, ...]] = ("id", "type")
    id: Mapped[UUID] = columns.uuid_primary_key()
    created: Mapped[datetime] = columns.created_field()
    updated: Mapped[datetime] = columns.updated_field()
    type: Mapped[str] = mapped_column(index=True, init=False)
    deleted: Mapped[datetime | None] = columns.deleted_field()

    @declared_attr  # type: ignore
    def __mapper_args__(cls) -> dict[str, str]:  # noqa: N805
        retval: dict[str, str] = {"polymorphic_identity": cls.__tablename__}
        if cls.__name__ == "Resource":  # type: ignore
            retval["polymorphic_on"] = "type"
        return retval

    @classmethod
    def __pydantic_type_from_class_attribute(cls, attr_name: str):
        attr: InstrumentedAttribute = cls.__dict__[attr_name]
        attr_type = attr.type.python_type
        return (
            (attr_type | None, Field(default=None))
            if attr.nullable
            else (attr_type, Field(default=...))
        )

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
        return create_model(  # type: ignore
            name,
            __config__=ConfigDict(extra="forbid"),
            **{  # type: ignore
                attr_name: cls.__pydantic_type_from_class_attribute(attr_name)
                for attr_name in cls.__dataclass_fields__
                if all([attr_name not in excluded, attr_name in included])
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

    @classmethod
    def primary_foreign_key_to(cls, *, init: bool) -> MappedColumn[UUID]:
        return mapped_column(
            ForeignKey(f"{cls.__tablename__}.id"), primary_key=True, init=init
        )


def create_resource_cls(base: type[base.Base]) -> type[Resource]:
    class Resource(MappedAsDataclass, base, ResourceAttributes, kw_only=True):
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            required_attributes = ("plural_name", "singular_name")
            for attr in required_attributes:
                if not hasattr(cls, attr):
                    raise TypeError(f"Subclass {cls.__name__} must define '{attr}'")

    return Resource  # type: ignore


if TYPE_CHECKING:

    class Resource(MappedAsDataclass, base.Base, ResourceAttributes, kw_only=True):
        """Shared attribute DB model/table"""

else:
    Resource = create_resource_cls(Base)


class ResourceAccess(MappedAsDataclass, Base, kw_only=True):
    resource_id: Mapped[UUID] = Resource.primary_foreign_key_to(init=True)
    user_id: Mapped[UUID] = User.primary_foreign_key_to(init=True)
    access: Mapped[AccessLevel]
    resource: Mapped[Resource] = relationship(lazy="joined", init=False)
    user: Mapped[User] = relationship(lazy="joined", init=False)


class ResourceAccessItem(BaseModel):
    user_id: UUID = Field(default=..., alias="user_id")
    access: AccessLevel


def update_modified_on_update_listener(_: Any, __: Any, target: Resource) -> None:
    """Event listener that runs before a record is updated, and sets the modified field accordingly."""
    # it's okay if this field doesn't exist - SQLAlchemy will silently ignore it.
    target.updated = datetime.now(tz=UTC)


# This actually makes the updated field work.
event.listen(
    Resource, "before_update", update_modified_on_update_listener, propagate=True
)
