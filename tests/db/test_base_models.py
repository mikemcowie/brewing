from typing import TYPE_CHECKING

from pydantic.alias_generators import to_snake
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr

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
