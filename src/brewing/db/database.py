"""Database: core database functionality."""

from __future__ import annotations

import asyncio
import importlib
import inspect
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import InitVar, dataclass, field
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import structlog
from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from brewing.cli import CLI, CLIOptions
from brewing.context import current_database
from brewing.db.migrate import Migrations
from brewing.db.settings import DatabaseType, load_db_config
from brewing.db.utilities import find_calling_frame

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.orm import DeclarativeBase

    from brewing import Brewing
    from brewing.db.types import DatabaseConnectionConfiguration


logger = structlog.get_logger()

_CURRENT_DB_SESSION: ContextVar[AsyncSession | None] = ContextVar(
    "current_session", default=None
)


@dataclass
class Database:
    """Object encapsulating fundamental context of a service's sql database."""

    # We go to significant lengths to make the declarative base live through pickling.
    # even if its metadata references something unpickleable.
    # we don't directly attach the base to the class, instead we pass it as ab initvar,
    # store only a string reference to it in __post_init__, and recover the Base via importlib
    # as a cached property.
    base: InitVar[type[DeclarativeBase]] = field()  # pyright: ignore[reportRedeclaration]
    revisions_directory: Path = field(
        default_factory=lambda: Path(
            find_calling_frame(inspect.stack(), __file__).filename
        ).parent
        / "revisions"
    )
    db_type: DatabaseType | None = None

    def __post_init__(self, base: type[DeclarativeBase]):  # pyright: ignore[reportGeneralTypeIssues]
        self._base_ref = base.__module__, base.__name__
        mod, attr = self._base_ref
        if getattr(importlib.import_module(mod), attr) is not base:
            raise TypeError(f"{base} must match the {attr} attribute of module {mod}")
        self._engine: dict[asyncio.AbstractEventLoop, AsyncEngine] = {}

    def __getstate__(self):
        """Override the attributes dumped when the object is pickled.

        This is used to bypass pickling the fastapi instance, which instead
        will be recreated as a cached property on first call after unpicking,
        """
        state = self.__dict__.copy()
        state.pop("migrations", None)
        state.pop("cli", None)
        state.pop("metadata", None)
        state.pop("base_", None)
        _engine: dict[str, Any] | None = state.get("_engine")
        if _engine:
            _engine.clear()
        return state

    def register(self, name: str, brewing: Brewing, /):
        """Register database to brewing."""
        brewing.cli.typer.add_typer(self.cli.typer, name=name)

    @cached_property
    def base_(self) -> type[DeclarativeBase]:
        """Return the declarative base being used for this db."""
        mod, attr = self._base_ref
        return getattr(importlib.import_module(mod), attr)

    @cached_property
    def metadata(self) -> MetaData:
        """The sqlalchemy metadata associated with the declarative base."""
        return self.base_.metadata

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
        async with self.engine.begin() as conn:
            while True:
                try:
                    await conn.execute(text("SELECT 1"))
                except Exception:
                    if (datetime.now(UTC) - start).total_seconds() > timeout:
                        raise
                    logger.exception("database not alive")
                else:
                    return True

    @cached_property
    def migrations(self) -> Migrations:
        """Database migrations provider."""
        return Migrations(
            database=self,
            revisions_dir=self.revisions_directory,
        )

    @cached_property
    def config(self) -> DatabaseConnectionConfiguration:
        """Database configuration object."""
        return load_db_config(self.db_type.value if self.db_type else None)

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
async def db_session() -> AsyncGenerator[AsyncSession]:
    db = current_database()
    if session := _CURRENT_DB_SESSION.get():
        yield session
        return
    async with AsyncSession(bind=db.engine, expire_on_commit=False) as session:
        token = _CURRENT_DB_SESSION.set(session)
        yield session
        _CURRENT_DB_SESSION.reset(token)
        await session.commit()
