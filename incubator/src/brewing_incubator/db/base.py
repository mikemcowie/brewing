from pydantic.alias_generators import to_snake
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr

metadata = MetaData()


class Base(DeclarativeBase):
    __abstract__ = True
    metadata = metadata

    @declared_attr  # type: ignore
    def __tablename__(cls) -> str:  # noqa: N805
        return to_snake(cls.__name__)
