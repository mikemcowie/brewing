from functools import cache
from typing import TYPE_CHECKING

from brewinglib.db.types import DatabaseConnectionConfiguration
from brewinglib.generic import runtime_generic
from sqlalchemy.ext.asyncio import create_async_engine

if not TYPE_CHECKING:
    create_async_engine = cache(create_async_engine)


@runtime_generic
class Database[ConfigT: DatabaseConnectionConfiguration]:
    config_type: type[ConfigT]

    @property
    def engine(self):
        return create_async_engine(url=self.config_type().url())
