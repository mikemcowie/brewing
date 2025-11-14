"""Database: core database functionality."""

from __future__ import annotations
import functools
import asyncio
from datetime import datetime, UTC
import inspect
from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager
from functools import cached_property
from pathlib import Path
from typing import Literal, TYPE_CHECKING
import structlog

from brewing.cli import CLI, CLIOptions
from brewing.db.migrate import Migrations
from brewing.db.types import DatabaseConnectionConfiguration
from brewing.generic import runtime_generic
from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine

if TYPE_CHECKING:
    from brewing import Brewing


logger = structlog.get_logger()


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
        self._engine: dict[asyncio.AbstractEventLoop, AsyncEngine] = {}

    def register(self, name: str, brewing: Brewing, /):
        """Register database to brewing."""
        brewing.cli.typer.add_typer(self.cli.typer, name=name)

    @cached_property
    def cli(self) -> CLI[CLIOptions]:
        """Typer CLI for the database."""
        return CLI(
            CLIOptions("db"),
            wraps=self.migrations,
            help="Manage the database and its migrations.",
        )

    @property
    def metadata(self) -> tuple[MetaData, ...]:
        """Tuple of sqlalchemy metadata."""
        return self._metadata

    async def is_alive(self, timeout: float = 1.0) -> Literal[True]:
        """
        Return True when the database can be connected to.

        Retry until timeout has elapsed.
        """
        start = datetime.now(UTC)
        async with self.session() as session:
            while True:
                try:
                    await session.execute(text("SELECT 1"))
                    return True
                except Exception as error:
                    if (datetime.now(UTC) - start).total_seconds() > timeout:
                        raise
                    logger.error(f"database not alive, {str(error)}")

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
        return self.config_type.database_type

    @property
    def engine(self):
        """Sqlalchemy async engine."""
        loop = asyncio.get_running_loop()
        if current := self._engine.get(loop):
            return current
        # If we are making a new loop, opportunistically we can check
        # if we can remove any non-running event loops.
        for other_loop in list(self._engine.keys()):
            if not other_loop.is_running():
                del self._engine[other_loop]
        self._engine[loop] = create_async_engine(self.config.url())
        return self._engine[loop]

    def force_clear_engine(self):
        """
        Force clear the engine.

        This is required to reset the database instance in tests
        when we may not have an active event loop.
        """
        self._engine.clear()
        self._config = None

    async def clear_engine(self):
        """Clear the engine cleanly, dropping connections."""
        if self.engine:
            await self.engine.dispose()
        self.force_clear_engine()

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
