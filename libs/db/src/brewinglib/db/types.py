from __future__ import annotations

from contextlib import (
    asynccontextmanager,
)
from typing import TYPE_CHECKING, ClassVar, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from brewinglib.db.migrate import Migrations
    from brewinglib.db.settings import DatabaseType
    from sqlalchemy import MetaData
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import AsyncEngine


class DatabaseProtocol(Protocol):
    @property
    def engine(self) -> AsyncEngine: ...

    @property
    def database_type(self) -> DatabaseType: ...

    @property
    def metadata(self) -> tuple[MetaData, ...]: ...

    @property
    def config(self) -> DatabaseConnectionConfiguration: ...

    @property
    def migrations(self) -> Migrations: ...

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        raise NotImplementedError()
        yield AsyncSession()


class DatabaseConnectionConfiguration(Protocol):
    """Protocol for loading database connections.

    Connections are expected to be loaded from environment variables
    per 12-factor principals, so no arguments are accepted in the constructor.
    """

    database_type: ClassVar[DatabaseType]

    def __init__(self): ...
    def url(self) -> URL: ...
