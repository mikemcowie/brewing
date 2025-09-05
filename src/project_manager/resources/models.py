from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, create_model
from sqlalchemy import ForeignKey
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    MappedColumn,
    declared_attr,
    mapped_column,
)

from project_manager import db

TypeBaseModel = type[BaseModel]


@dataclass
class ResourceSchemas:
    create: type[BaseModel]
    summary: type[BaseModel]
    read: type[BaseModel]
    update: type[BaseModel]


class Resource(MappedAsDataclass, db.Base, kw_only=True):
    read_only_fields: ClassVar[tuple[str, ...]] = ("id", "created", "updated", "type")
    summary_fields: ClassVar[tuple[str, ...]] = ("id", "type")
    id: Mapped[UUID] = db.uuid_primary_key()
    created: Mapped[datetime] = db.created_field()
    updated: Mapped[datetime] = db.updated_field()
    type: Mapped[str] = mapped_column(index=True, init=False)

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
        return ResourceSchemas(
            create=cls.create_new_model(
                f"Create{cls.__name__}", excluded=cls.read_only_fields
            ),
            summary=cls.create_new_model(
                f"Summary{cls.__name__}", included=cls.summary_fields
            ),
            read=cls.create_new_model(
                f"Read{cls.__name__}", included=cls.summary_fields
            ),
            update=cls.create_new_model(
                f"Update{cls.__name__}", excluded=cls.read_only_fields
            ),
        )

    @staticmethod
    def primary_foreign_key_to() -> MappedColumn[UUID]:
        return mapped_column(ForeignKey("resource.id"), primary_key=True, init=False)
