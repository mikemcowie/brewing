"""Database: core database functionality."""

import asyncio
import functools
import inspect
from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager
from functools import cache, cached_property
from pathlib import Path
from typing import Any

from brewing.cli import CLI
from brewing.db.migrate import Migrations
from brewing.db.types import DatabaseConnectionConfiguration
from brewing.generic import runtime_generic
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


@cache
def _provide_cached_engine(
    event_loop: asyncio.EventLoop | None,  # noqa: ARG001
    *args: Any,
    **kwargs: Any,
):
    return create_async_engine(*args, **kwargs)


def _find_calling_file(stack: list[inspect.FrameInfo]):
    for frameinfo in stack:
        if frameinfo.filename not in (__file__, functools.__file__):
            return Path(frameinfo.filename)
    raise RuntimeError("Could not find calling file.")


@runtime_generic
class Database[ConfigT: DatabaseConnectionConfiguration]:
    """Object encapsulating fundamental context of a service's sql database."""

    config_type: type[ConfigT]

    def __init__(
        self,
        metadata: MetaData | Iterable[MetaData],
        revisions_directory: Path | None = None,
    ):
        metadata = (metadata,) if isinstance(metadata, MetaData) else tuple(metadata)
        self._metadata = metadata
        self._revisions_directory = (
            revisions_directory
            or _find_calling_file(inspect.stack()).parent / "revisions"
        )
        self._config: ConfigT | None = None
        self._migrations: Migrations | None = None

    @cached_property
    def cli(self) -> CLI:
        """Typer CLI for the database."""
        return CLI("db", wraps=self.migrations)

    @property
    def metadata(self) -> tuple[MetaData, ...]:
        """Tuple of sqlalchemy metadata."""
        return self._metadata

    @property
    def migrations(self) -> Migrations:
        """Database migrations provider."""
        if not self._migrations:
            self._migrations = Migrations(
                database=self,
                revisions_dir=self._revisions_directory,
            )
        return self._migrations

    @property
    def config(self) -> ConfigT:
        """Database configuration object."""
        if not self._config:
            self._config = self.config_type()
        return self._config

    @property
    def database_type(self):
        """The database type."""
        return self.config.database_type

    @property
    def engine(self):
        """Sqlalchemy async engine."""
        try:
            event_loop = asyncio.get_running_loop()
        except RuntimeError:
            event_loop = None
        return _provide_cached_engine(event_loop, url=self.config_type().url())

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        """
        Provide an async orm session for the database.

        Returns:
            AsyncGenerator[AsyncSession]: _description_

        Yields:
            Iterator[AsyncGenerator[AsyncSession]]: _description_

        """
        async with AsyncSession(bind=self.engine, expire_on_commit=False) as session:
            yield session
