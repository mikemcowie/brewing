"""Protocols and type declarations for the brewing.db package."""

from __future__ import annotations

from contextlib import (
    asynccontextmanager,
)
from typing import TYPE_CHECKING, ClassVar, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from brewing.db.migrate import Migrations
    from brewing import Brewing
    from brewing.db.settings import DatabaseType
    from sqlalchemy import MetaData
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import AsyncEngine


class DatabaseProtocol(Protocol):
    """Protocol for database objects."""

    def register(self, name: str, brewing: Brewing, /):
        """Rgister the database with brewing."""

    @property
    def engine(self) -> AsyncEngine:
        """Cached async engine associated with the database."""
        ...

    def force_clear_engine(self):
        """
        Force clear the engine.

        This is required to reset the database instance in tests
        when we may not have an active event loop.
        """
        ...

    async def clear_engine(self) -> None:
        """Clear the engine cleanly, dropping connections."""
        ...

    async def is_alive(self, timeout: float = 1.0) -> bool:
        """Return true if we can connect to the database."""
        ...

    @property
    def database_type(self) -> DatabaseType:
        """Database type associated with the object."""
        ...

    @property
    def metadata(self) -> tuple[MetaData, ...]:
        """Tuple of sqlalchemy metadata objects."""
        ...

    @property
    def config(self) -> DatabaseConnectionConfiguration:
        """Configuration associated with the database."""
        ...

    @property
    def migrations(self) -> Migrations:
        """Return associated Migrations object."""
        ...

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        """Yield an async sqlalchemy orm session."""
        raise NotImplementedError()
        yield AsyncSession()


class DatabaseConnectionConfiguration(Protocol):
    """
    Protocol for loading database connections.

    Connections are expected to be loaded from environment variables
    per 12-factor principals, so no arguments are accepted in the constructor.
    """

    database_type: ClassVar[DatabaseType]

    def __init__(self): ...
    def url(self) -> URL:
        """Return the sqlalchemy URL for the database."""
        ...
