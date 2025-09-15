from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from contextlib import AbstractAsyncContextManager

    from sqlalchemy import MetaData
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


class DatabaseProtocol(Protocol):
    metadata: MetaData

    @property
    def engine(self) -> AsyncEngine: ...


class DatabaseConnectionConfiguration(Protocol):
    """Protocol for loading database connections.

    Connections are expected to be loaded from environment variables
    per 12-factor principals, so no arguments are accepted in the constructor.
    """

    def __init__(self): ...
    def url(self) -> URL: ...

    async def session(
        self,
    ) -> AbstractAsyncContextManager[AsyncGenerator[AsyncSession]]: ...
