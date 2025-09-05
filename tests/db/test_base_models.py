from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_snake
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr

from project_manager.resources.models import (
    Resource,
    create_resource_cls,
)


def create_test_resource_cls():
    class Base(DeclarativeBase):
        __abstract__ = True
        metadata = MetaData()

        @declared_attr  # type: ignore
        def __tablename__(cls) -> str:  # noqa: N805
            return to_snake(cls.__name__)

    if TYPE_CHECKING:
        return Resource
    else:
        return create_resource_cls(Base)


def test_test_resource_cls():
    assert Resource.metadata is not create_test_resource_cls().metadata


def test_plural_name_must_be_defined():
    resource = create_test_resource_cls()

    with pytest.raises(TypeError) as err:

        class SubResource(resource):
            id = resource.primary_foreign_key_to(init=True)

    assert "TypeError: Subclass SubResource must define 'plural_name'" in err.exconly()


class TestSchemaGeneration:
    def db_model(self):
        resource = create_test_resource_cls()

        class SomeResource(resource, kw_only=True):
            id: Mapped[UUID] = Resource.primary_foreign_key_to(init=False)
            name: Mapped[str]
            optional: Mapped[str | None]

            read_only_fields = ("name", "optional")

        return SomeResource

    @pytest.mark.xfail(reason="Need rework to pass")
    def test_create_model(self):
        class CreateSomeResource(BaseModel):
            model_config = ConfigDict(extra="forbid")
            name: str
            optional: str | None = Field(default=None)

        assert str(self.db_model().schemas().create.model_fields) == str(
            CreateSomeResource.model_fields
        )
        assert self.db_model().schemas().create.__name__ == CreateSomeResource.__name__
        assert (
            self.db_model().schemas().create.model_json_schema()
            == CreateSomeResource.model_json_schema()
        )

    @pytest.mark.xfail(reason="Need rework to pass")
    def test_read_model(self):
        class ReadSomeResource(BaseModel):
            model_config = ConfigDict(extra="forbid")
            id: UUID
            created: datetime
            updated: datetime
            type: str
            name: str
            optional: str | None = Field(default=None)

        assert str(self.db_model().schemas().read.model_fields) == str(
            ReadSomeResource.model_fields
        )
        assert self.db_model().schemas().create.__name__ == ReadSomeResource.__name__
        assert (
            self.db_model().schemas().read.model_json_schema()
            == ReadSomeResource.model_json_schema()
        )
