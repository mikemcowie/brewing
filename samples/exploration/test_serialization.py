"""API Design Exploration - converting between sqlalchemy and pydantic with explicit or implicit serialization configurations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING, Any, TypeVar, assert_never, get_type_hints

import pytest
import sqlalchemy as sa
from brewinglib.generic import runtime_generic
from pydantic import BaseModel, ConfigDict, Field, create_model
from pydantic.alias_generators import to_snake
from pydantic.errors import PydanticSchemaGenerationError
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    RelationshipProperty,
    declared_attr,
    mapped_column,
    relationship,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class ModelInfo[ModelT: DeclarativeBase]:
    model: type[ModelT] = field(init=True)
    columns: dict[str, sa.Column[Any]] = field(init=False)
    relationships: dict[str, RelationshipProperty[Any]] = field(init=False)
    primary_key_columns: dict[str, sa.ColumnElement[Any]] = field(init=False)
    type_hints: dict[str, Any] = field(init=False, repr=False)

    def __post_init__(self):
        inspected = sa.inspect(self.model)
        self.columns = {col.name: col for col in inspected.columns}
        self.relationships = {r.key: r for r in inspected.relationships}
        self.primary_key_columns = {col.name: col for col in inspected.primary_key}
        self.type_hints = get_type_hints(self.model)


type AnnotationType = Any
type PydanticField = Any

type AnnotationAndField = tuple[AnnotationType, PydanticField]


def field_of(item: Any):
    if isinstance(item, sa.Column):
        default = item.default or ...
        return Field(default=default)
    if isinstance(item, RelationshipProperty):
        return Field(default=...)
    assert_never("no other types expected here?")


class FieldNotOnModel(RuntimeError):
    pass


class FieldMatchesMultipleTypes(RuntimeError):
    pass


class ExplicitSerializationRequired(RuntimeError):
    """Raised for type annotations found in sqlalchemty models which can't be directly used in pydantic.

    For example, a `Mapped[RelatedModel] type annotation denoting a relationship via a foreign key
    where RelatedModel is a sqlalchemy model which pydantic can't automatically handle.
    """


ModelT = TypeVar("ModelT", bound=DeclarativeBase)
type FieldSerialization = str | tuple[str, ModelSerialization[Any]]


@runtime_generic
class ModelSerialization[ModelT: DeclarativeBase]:
    """Configires how a pydantic model is generated from sqlalchemy model."""

    model: type[ModelT]

    def __init__(
        self,
        name: str,
        *,
        fields: Sequence[FieldSerialization],
        model: type[ModelT] | None = None,
    ):
        try:
            self.model = model or self.model
        except AttributeError as error:
            raise TypeError(
                "model must be provided either as a class variable or an inititalization parameter."
            ) from error
        self.name = name
        self.fields = fields
        self.model_info = ModelInfo(self.model)

    def _pydantic_annotation_and_field(self, field: FieldSerialization, name: str):
        candidate_items: list[sa.Column[Any] | RelationshipProperty[Any]] = [
            item
            for item in [
                self.model_info.columns.get(name),
                self.model_info.relationships.get(name),
            ]
            if item is not None
        ]

        if not candidate_items:
            raise FieldNotOnModel(
                f"{self.model} has no field with {name=}, available fields {[self._field_name(field) for field in self.fields]}"
            )
        if len(candidate_items) > 1:
            raise FieldMatchesMultipleTypes(
                f"{field=} matches multiple fields on {self.model=}. Can't work out what to do next."
            )
        item = candidate_items[0]
        if isinstance(field, tuple):
            return field[1].schema, field_of(item)
        annotation = self.model_info.type_hints[name].__args__[0]
        # We test if the annotation is something pydantic can use by attempting to make a model with just that type:
        try:
            create_model("TestAnnotation", test=(annotation, ...))
        except PydanticSchemaGenerationError as error:
            raise ExplicitSerializationRequired(
                f"Cannot created a schema from {annotation=}. "
                "An explicit ModelSerialization needs to be configured for this field."
            ) from error
        return annotation, field_of(item)

    @staticmethod
    def _field_name(field_sz: FieldSerialization):
        if isinstance(field_sz, str):
            return field_sz
        return field_sz[0]

    @cached_property
    def schema(self) -> type[BaseModel]:
        return create_model(
            self.name,
            __config__=ConfigDict(extra="forbid"),
            __doc__=self.model.__doc__,
            **{
                self._field_name(field): self._pydantic_annotation_and_field(
                    field, self._field_name(field)
                )
                for field in self.fields
            },
        )

    def __str__(self):
        """We rely on the str method as the key on the pydantic model."""
        return self.name


class Base(DeclarativeBase):
    @declared_attr  # type: ignore
    def __tablename__(cls) -> str:  # noqa: N805
        return to_snake(cls.__name__)


class ModelWithSimpleTypes(Base):
    """A basic model."""

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    optional_description: Mapped[str | None] = mapped_column()
    created: Mapped[datetime] = mapped_column()
    deleted: Mapped[datetime | None] = mapped_column()


class FullSchema(BaseModel):
    """A basic model."""

    model_config = ConfigDict(extra="forbid")
    id: int
    name: str
    optional_description: str | None
    created: datetime
    deleted: datetime | None


def test_model_must_be_initialized_via_either_generic_or_init():
    # good
    ModelSerialization[ModelWithSimpleTypes]("something", fields=[])
    # also good
    ModelSerialization("something", fields=[], model=ModelWithSimpleTypes)
    # type error but works at runtime
    ModelSerialization[ModelWithSimpleTypes](
        "something", fields=[], model=ModelWithSimpleTypes
    )  # type: ignore
    # bad
    with pytest.raises(TypeError):
        ModelSerialization("something", fields=[])


def test_full_schema():
    assert (
        ModelSerialization[ModelWithSimpleTypes](
            "FullSchema",
            fields=("id", "name", "optional_description", "created", "deleted"),
        ).schema.model_json_schema()
        == FullSchema.model_json_schema()
    )


class ModelWithRelationships(Base):
    """A basic model."""

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    optional_description: Mapped[str | None] = mapped_column()
    created: Mapped[datetime] = mapped_column()
    deleted: Mapped[datetime | None] = mapped_column()
    many_one_related_model_id: Mapped[int] = mapped_column(
        sa.ForeignKey("many_one_related_model.id")
    )
    many_one_related_model: Mapped[list[ManyOneRelatedModel]] = relationship()


class ManyOneRelatedModel(Base):
    """A related model."""

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    optional_description: Mapped[str | None] = mapped_column()
    created: Mapped[datetime] = mapped_column()
    deleted: Mapped[datetime | None] = mapped_column()


# Generated pydantic model expected to match this in json_schema.
class ModelWithRelationshiopsSchema(BaseModel):
    """A basic model."""

    model_config = ConfigDict(extra="forbid")
    id: int
    name: str
    optional_description: str | None
    created: datetime
    deleted: datetime | None
    many_one_related_model: ManyOneRelatedModelSchema


class ManyOneRelatedModelSchema(BaseModel):
    """A related model."""

    model_config = ConfigDict(extra="forbid")
    id: int
    name: str
    optional_description: str | None


def test_related_schema():
    s = ModelSerialization[ModelWithRelationships](
        "ModelWithRelationshiopsSchema",
        fields=(
            "id",
            "name",
            "optional_description",
            "created",
            "deleted",
            (
                "many_one_related_model",
                ModelSerialization(
                    "ManyOneRelatedModelSchema",
                    fields=("id", "name", "optional_description"),
                    model=ManyOneRelatedModel,
                ),
            ),
        ),
    )
    assert (
        s.schema.model_json_schema()
        == ModelWithRelationshiopsSchema.model_json_schema()
    )
