"""Protocols and type declarations for the brewing.db package."""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import TYPE_CHECKING, ClassVar, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from sqlalchemy import MetaData
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import AsyncEngine

    from brewing import Brewing
    from brewing.db.migrate import Migrations
    from brewing.db.settings import DatabaseType


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

    @asynccontextmanager
    async def current_session(self) -> AsyncGenerator[AsyncSession]:
        """Yield a current session in a context manager.

        The same session will be returned repeatedly when called
        within a context.
        """
        raise NotImplementedError()
        yield AsyncSession()

    @contextmanager
    def __call__(self) -> Generator[None]:
        """Set database as the global database."""
        raise NotImplementedError()
        yield

    def push(self):
        """Push the current database instance to the global context."""


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
