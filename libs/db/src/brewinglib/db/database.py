from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import cache
from typing import TYPE_CHECKING

from brewinglib.db.types import DatabaseConnectionConfiguration
from brewinglib.generic import runtime_generic
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

if not TYPE_CHECKING:
    create_async_engine = cache(create_async_engine)


@runtime_generic
class Database[ConfigT: DatabaseConnectionConfiguration]:
    config_type: type[ConfigT]

    def __init__(self, /, metadata: MetaData | None = None):
        self._metadata = metadata or MetaData()

    @property
    def metadata(self) -> MetaData:
        return self._metadata

    @property
    def engine(self):
        return create_async_engine(url=self.config_type().url())

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        async with AsyncSession(bind=self.engine) as session:
            yield session
