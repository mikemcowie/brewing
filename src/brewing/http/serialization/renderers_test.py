from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace as SN  # noqa: N817
from typing import Unpack
from uuid import UUID

import pytest
import sqlalchemy as sa
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from brewing.http.serialization.renderers import (
    PydanticValidateArgs,
    SimpleRenderer,
    SQLAlchemyORMRenderer,
)


class TestSimpleRenderer:
    class DataModel(BaseModel):
        foo: str
        bar: int

    def get_renderer(self, **kwargs: Unpack[PydanticValidateArgs]):
        return SimpleRenderer(self.DataModel, **kwargs)

    def test_raises_missing_attr(self):
        renderer = self.get_renderer(from_attributes=True)
        with pytest.raises(ValidationError):
            renderer(object())

    def test_raises_from_attributes_false(self):
        renderer = self.get_renderer(from_attributes=False)
        with pytest.raises(ValidationError):
            renderer(SN(foo="v1", bar=1))

    def test_renders_from_attributes(self):
        renderer = self.get_renderer(from_attributes=True)
        assert renderer(SN(foo="v1", bar=1)) == self.DataModel(foo="v1", bar=1)

    def test_renders_dict(self):
        renderer = self.get_renderer(from_attributes=False)
        assert renderer({"foo": "v1", "bar": 1}) == self.DataModel(foo="v1", bar=1)


class Base(DeclarativeBase):
    pass


class SerMod1(Base):
    __tablename__ = "ser_mod_1"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    f1: Mapped[str] = mapped_column()
    f2: Mapped[str] = mapped_column()
    f3: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    s2: Mapped[list[SerMod2]] = relationship(back_populates="s1")


class SerMod2(Base):
    __tablename__ = "ser_mod_2"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    h1: Mapped[str] = mapped_column()
    s1_id: Mapped[int] = mapped_column(sa.ForeignKey(SerMod1.id))
    s1: Mapped[SerMod1] = relationship()


class _OverridenMixin:
    id: Mapped[int] = mapped_column(primary_key=True)


class SerMod3(_OverridenMixin, Base):
    """Used to test inheritence. Note the id is overriden to a different type.

    We'll test that the __mro__ method is respected when building a pydantic model from it.
    """

    __tablename__ = "ser_mod_3"
    id: Mapped[UUID] = mapped_column(primary_key=True)  # pyright: ignore[reportIncompatibleVariableOverride]
    s2_id: Mapped[int] = mapped_column(sa.ForeignKey(SerMod2.id))


class SerMod4(Base):
    __tablename__ = "ser_mod_4"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    f1: Mapped[str] = mapped_column()
    f2: Mapped[str] = mapped_column()
    f3: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))

    @property
    def annotated_property(self) -> str:
        return self.f1 + self.f2

    @property
    def unannotated_property(self):
        return self.f1 + self.f2

    @hybrid_property
    def hybrid_annotated_property(self) -> str:
        return self.f1 + self.f2


class TestSQLAlchemyORMRenderer:
    def test_model_generated_matches(self):
        class SerMod1Schema(BaseModel):
            id: int
            f1: str
            f2: str
            f3: datetime
            s2: list["SerMod2Schema"]

        class SerMod2Schema(BaseModel):
            id: int
            h1: str

        SerMod1Schema.model_rebuild()

        renderer = SQLAlchemyORMRenderer(SerMod1, lambda t: f"{t.__name__}Schema")
        assert (
            renderer.create_model().model_json_schema()
            == SerMod1Schema.model_json_schema()
        )

    def test_inheritance_attributes_mro_is_respeced(self):
        renderer = SQLAlchemyORMRenderer(SerMod3, lambda t: f"{t.__name__}Schema")
        assert (
            renderer.create_model().model_json_schema()["properties"]["id"]["format"]
            == "uuid"
        )

    def test_property_with_return_annotation_is_included(self):
        class SerMod4Schema(BaseModel):
            id: int
            f1: str
            f2: str
            f3: datetime
            annotated_property: str
            hybrid_annotated_property: str

        renderer = SQLAlchemyORMRenderer(SerMod4, lambda t: f"{t.__name__}Schema")
        assert (
            renderer.create_model().model_json_schema()
            == SerMod4Schema.model_json_schema()
        )
