"""
Declarative base factory for brewing.db .

We provide a new_base factory, which ensures a new base with a fresh metadata
is available. It's not important to use it - any old declarative base class will do;
but it has nicenesses like auto column naming.
"""

from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from pydantic.alias_generators import to_snake
from sqlalchemy import orm


class Base(orm.MappedAsDataclass, orm.DeclarativeBase, kw_only=True):
    """Brewing's Declarative base class.

    "Features" above standard sqlalchemy declarative base:

    1. Always uses orm.MappedAsDataclass with kw_only=True
    2. enforces that a generated subclass must be __abstract__
    """

    if not TYPE_CHECKING:
        # Allowing type checker to see these methods makes completions much worse.

        def __init_subclass__(cls, *args: Any, **kwargs: Any) -> None:
            if cls.__mro__[1] is Base:
                cls.__abstract__ = True
                cls.metadata = sa.MetaData()
            return super().__init_subclass__(*args, **kwargs)

        @orm.declared_attr  # type: ignore
        def __tablename__(cls) -> str:  # noqa: N805
            return to_snake(cls.__name__)


def new_base():
    """Return a new base class with a new metadata."""

    class OurBase(Base):
        """A custom base used for tests."""

    return OurBase
