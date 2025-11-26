"""Database: core database functionality."""

from __future__ import annotations

import asyncio
import functools
import inspect
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import structlog
from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from brewing.cli import CLI, CLIOptions
from brewing.db.migrate import Migrations

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from brewing import Brewing
    from brewing.db.types import DatabaseConnectionConfiguration


logger = structlog.get_logger()


def _find_calling_file(stack: list[inspect.FrameInfo]):
    for frameinfo in stack:
        if (
            frameinfo.filename not in (__file__, functools.__file__)
            and ".py" in frameinfo.filename
        ):
            return Path(frameinfo.filename)
    raise RuntimeError("Could not find calling file.")


@dataclass
class Database:
    """Object encapsulating fundamental context of a service's sql database."""

    config_type: type[DatabaseConnectionConfiguration]
    metadata: MetaData = field(
        compare=False
    )  # Exclude Metadata from equality operation as it doesn't have a sane equality method.
    revisions_directory: Path = field(
        default_factory=lambda: _find_calling_file(inspect.stack()).parent / "revisions"
    )

    def __post_init__(self):
        self._config: DatabaseConnectionConfiguration | None = None
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
                except Exception:
                    if (datetime.now(UTC) - start).total_seconds() > timeout:
                        raise
                    logger.exception("database not alive")
                else:
                    return True

    @cached_property
    def migrations(self) -> Migrations:
        """Database migrations provider."""
        if not self._migrations:
            self._migrations = Migrations(
                database=self,
                revisions_dir=self.revisions_directory,
            )
        return self._migrations

    @property
    def config(self) -> DatabaseConnectionConfiguration:
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
