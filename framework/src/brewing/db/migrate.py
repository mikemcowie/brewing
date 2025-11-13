"""Support for database migrations based on alembic."""

from __future__ import annotations

import logging
import asyncio
from contextvars import ContextVar, Token
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from alembic import command, context
from alembic.config import Config as AlembicConfig

if TYPE_CHECKING:
    from brewing.db.types import DatabaseProtocol
    from sqlalchemy.engine import Connection

MIGRATIONS_CONTEXT_DIRECTORY = Path(__file__).parent / "_migrationcontext"


alembic_logger = logging.getLogger("alembic")
alembic_logger.setLevel(logging.INFO)
alembic_handler = logging.StreamHandler()
alembic_handler.setLevel(logging.INFO)
alembic_logger.handlers.clear()
alembic_logger.addHandler(alembic_handler)


class MigrationsConfigError(RuntimeError):
    """raised for invalid migrations config states."""


class Migrations:
    """Controls migrations."""

    active_instance: ClassVar[ContextVar[Migrations]] = ContextVar("current_config")

    def __init__(
        self,
        database: DatabaseProtocol,
        revisions_dir: Path,
    ):
        self._database = database
        self._revisions_dir = revisions_dir
        self._runner = MigrationRunner(self)
        self._token: Token[Migrations] | None = None
        self._alembic = AlembicConfig()
        self._alembic.set_main_option(
            "script_location", str(MIGRATIONS_CONTEXT_DIRECTORY)
        )
        self._alembic.set_main_option("version_locations", str(revisions_dir))
        self._alembic.set_main_option("path_separator", ";")
        self._alembic.set_main_option("file_template", "rev_%%(rev)s_%%(slug)s")

    @property
    def database(self) -> DatabaseProtocol:
        """The database instance used by the migrations."""
        return self._database

    @property
    def metadata(self):
        """Tuple of sqlalchemy metadata."""
        return self._database.metadata

    @property
    def engine(self):
        """Async engine."""
        return self._database.engine

    @property
    def runner(self):
        """Object containing alembic env implementation."""
        return self._runner

    @property
    def revisions_dir(self):
        """The directory that database revisions are found in."""
        return self._revisions_dir

    @property
    def alembic(self):
        """Alembic config class instance."""
        return self._alembic

    def __enter__(self):
        """Set the migrations context to allow alembic to be invoked."""
        self._token = self.active_instance.set(self)

    def __exit__(self, *_: Any, **__: Any):
        """Cleanup context."""
        if self._token:
            self.active_instance.reset(self._token)
            self._token = None

    def generate_revision(self, message: str, autogenerate: bool = True):
        """Generate a new migration."""
        # late import as libraries involved may not be installed.
        from brewing.db import testing  # noqa: PLC0415

        with (
            testing.testing(self._database.database_type),
            self,
        ):
            command.upgrade(self.alembic, "head")
            command.revision(
                self._alembic,
                rev_id=f"{len(list(self._revisions_dir.glob('*.py'))):05d}",
                message=message,
                autogenerate=autogenerate,
            )

    @contextmanager
    def add_context(self, dev: bool):
        """If in dev context, run any dev context needed before proceeding."""
        from brewing.db import testing  # noqa: PLC0415

        context = testing.dev if dev else testing.noop  # type: ignore
        with context(self._database.database_type):
            yield

    def upgrade(self, revision: str = "head", dev: bool = False):
        """Upgrade the database."""
        with self.add_context(dev), self:
            command.upgrade(self._alembic, revision=revision)

    def downgrade(self, revision: str, dev: bool = False):
        """Downgrade the database."""
        with self.add_context(dev), self:
            command.downgrade(self._alembic, revision=revision)

    def stamp(self, revision: str, dev: bool = False):
        """Write to the versions table as if the database is set to the given revision."""
        with self.add_context(dev), self:
            command.stamp(self._alembic, revision=revision)

    def current(self, verbose: bool = False, dev: bool = False):
        """Display the current revision."""
        with self.add_context(dev), self:
            command.current(self._alembic, verbose=verbose)

    def check(self, dev: bool = False):
        """Validate that the database is updated to the latest revision."""
        with self.add_context(dev), self:
            command.check(self._alembic)


class MigrationRunner:
    """
    Our implementation of the logic normally in env.py.

    This can be customized in the same way env.py can normally be customized,
    but maintaining the machinery and CLI here.
    """

    def __init__(self, migrations: Migrations, /):
        self.migrations = migrations

    def run(self, connection: Connection) -> None:
        """Run migrations."""
        context.configure(
            connection=connection, target_metadata=self.migrations.metadata
        )

        with context.begin_transaction():
            context.run_migrations()

    async def arun(self) -> None:
        """
        Asyncronously run migrations.

        In this scenario we need to create an Engine
        and associate a connection with the context.

        """
        async with self.migrations.engine.begin() as connection:
            await connection.run_sync(self.run)

        await self.migrations.engine.dispose()

    def online(self) -> None:
        """Run migrations in 'online' mode."""
        asyncio.run(self.arun())

    def offline(self) -> None:
        """Run migrations in 'offline' mode."""
        raise NotImplementedError("offline mirations not supported.")


class NoActiveMigrationContext(RuntimeError):
    """No migration context has been enabled."""


def run():
    """Run migrations in the current context."""
    try:
        if migrations := Migrations.active_instance.get():
            if context.is_offline_mode():
                migrations.runner.offline()
            else:
                migrations.runner.online()
        else:
            raise RuntimeError("no current runner configured.")
    except AttributeError as err:
        raise NoActiveMigrationContext() from err
