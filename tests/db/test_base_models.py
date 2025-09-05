from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict
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


class TestSchemaGeneration:
    def db_model(self):
        resource = create_test_resource_cls()

        class SomeResource(resource, kw_only=True):
            id: Mapped[UUID] = Resource.primary_foreign_key_to(init=False)
            name: Mapped[str]
            optional: Mapped[str | None]

        return SomeResource

    def test_create_model(self):
        class CreateSomeResource(BaseModel):
            model_config = ConfigDict(extra="forbid")
            name: str
            optional: str

        assert str(self.db_model().schemas().create.model_fields) == str(
            CreateSomeResource.model_fields
        )
        assert self.db_model().schemas().create.__name__ == CreateSomeResource.__name__
        assert (
            self.db_model().schemas().create.model_json_schema()
            == CreateSomeResource.model_json_schema()
        )
