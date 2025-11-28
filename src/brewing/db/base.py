"""
Declarative base factory for brewing.db .

We provide a new_base factory, which ensures a new base with a fresh metadata
is available. It's not important to use it - any old declarative base class will do;
but it has nicenesses like auto column naming.
"""

import inspect

import sqlalchemy as sa
from pydantic.alias_generators import to_snake
from sqlalchemy import orm

from brewing.db.utilities import find_calling_frame


def new_base():
    """Return a new base class with a new metadata."""

    class Base(orm.MappedAsDataclass, orm.DeclarativeBase, kw_only=True):
        metadata = sa.MetaData()

        @orm.declared_attr  # type: ignore
        def __tablename__(cls) -> str:  # noqa: N805
            return to_snake(cls.__name__)

    Base.__module__ = find_calling_frame(inspect.stack(), __file__).frame.f_globals[
        "__name__"
    ]

    return Base
