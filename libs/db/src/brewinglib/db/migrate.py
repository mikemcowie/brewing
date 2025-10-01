"""Support for database migrations based on alembic."""

from __future__ import annotations

import asyncio
import contextlib
from contextvars import ContextVar
from dataclasses import dataclass
from functools import cached_property, partial
from pathlib import Path
from typing import TYPE_CHECKING

from alembic import command, context
from alembic.config import Config as AlembicConfig

if TYPE_CHECKING:
    from brewinglib.db.types import DatabaseProtocol
    from sqlalchemy.engine import Connection

MIGRATIONS_CONTEXT_DIRECTORY = Path(__file__).parent / "_migrationcontext"
type RevisionsDir = Path


### Begin configuration machery for alembic context
# This is basically working around the challenge of being hard to otherwise
# call the machinery in env.py with parameters.
# instead we use a contextvar, and `set_runner` contextmanager to set the value
# before alembic gets invoked, removing it after.

# configvar itself is private, as the 2 functions below it are the interface to it.
_current_config: ContextVar[MigrationsConfig] = ContextVar("current_config")


class MigrationsConfigError(RuntimeError):
    """raised for invalid migrations config states."""


@dataclass(frozen=True, kw_only=True)
class MigrationsConfig:
    database: DatabaseProtocol
    revisions_dir: RevisionsDir

    @cached_property
    def runner(self):
        return MigrationRunner(self)

    @property
    def engine(self):
        return self.database.engine

    @property
    def metadata(self):
        return self.database.metadata

    @cached_property
    def alembic(self) -> AlembicConfig:
        config = AlembicConfig()
        if not self.revisions_dir.is_dir():
            raise MigrationsConfigError(
                f"path {self.revisions_dir!s} is not a valid directory."
            )
        config.set_main_option("script_location", str(MIGRATIONS_CONTEXT_DIRECTORY))
        config.set_main_option("version_locations", str(self.revisions_dir))
        config.set_main_option("path_separator", ";")
        config.set_main_option("file_template", "rev_%%(rev)s_%%(slug)s")
        return config


@contextlib.contextmanager
def set_config(config: MigrationsConfig):
    token = _current_config.set(config)
    yield
    _current_config.reset(token)


_NO_DEFAULT = object()


def current_config[DefaultT](
    default: DefaultT = _NO_DEFAULT,
) -> DefaultT | MigrationsConfig:
    """Load the current migrations config.

    A default value can be passed, which if set, will be returned if
    LookupError is raised. Otherwise, raised LookupError if the config is not
    currently set.
    """
    try:
        return _current_config.get()
    except LookupError:
        if default is _NO_DEFAULT:
            raise
        return default


class Migrations:
    """Controls migrations."""

    def __init__(
        self,
        config: MigrationsConfig,
    ):
        self._config = config
        self._runner = MigrationRunner(config)
        self.set_config = partial(set_config, self._config)

    @property
    def config(self):
        return self._config

    def generate_revision(self, message: str, autogenerate: bool):
        """Generate a new migration."""
        # late import as libraries involved may not be installed.
        from brewinglib.db import testing  # noqa: PLC0415

        with (
            testing.testing(self.config.database.database_type),
            set_config(self._config),
        ):
            command.revision(
                self._config.alembic,
                rev_id=f"{len(list(self._config.revisions_dir.glob('*.py'))):05d}",
                message=message,
                autogenerate=autogenerate,
            )

    def upgrade(self, revision: str = "head"):
        """Upgrade the database"""
        with set_config(self._config):
            command.upgrade(self._config.alembic, revision=revision)

    def downgrade(self, revision: str):
        """Downgrade the database"""
        with set_config(self._config):
            command.downgrade(self._config.alembic, revision=revision)

    def stamp(self, revision: str):
        """Write to the versions table as if the database is set to the given revision."""
        with set_config(self._config):
            command.stamp(self._config.alembic, revision=revision)

    def current(self, verbose: bool = False):
        """Display the current revision."""
        with set_config(self._config):
            command.current(self._config.alembic, verbose=verbose)

    def check(self):
        """Validate that the database is updated to the latest revision."""
        with set_config(self._config):
            command.check(self._config.alembic)


class MigrationRunner:
    """Our implementation of the logic normally in env.py.

    This can be customized in the same way env.py can normally be customized,
    but maintaining the machinery and CLI here.
    """

    def __init__(self, config: MigrationsConfig, /):
        self._config = config

    def do_run_migrations(self, connection: Connection) -> None:
        context.configure(connection=connection, target_metadata=self._config.metadata)

        with context.begin_transaction():
            context.run_migrations()

    async def run_async_migrations(self) -> None:
        """In this scenario we need to create an Engine
        and associate a connection with the context.

        """
        async with self._config.engine.connect() as connection:
            await connection.run_sync(self.do_run_migrations)

        await self._config.engine.dispose()

    def run_migrations_online(self) -> None:
        """Run migrations in 'online' mode."""

        asyncio.run(self.run_async_migrations())

    def run_migrations_offline(self) -> None:
        raise NotImplementedError("offline mirations not supported.")


def run():
    if config := current_config(default=None):
        if context.is_offline_mode():
            config.runner.run_migrations_offline()
        else:
            config.runner.run_migrations_online()
    else:
        raise RuntimeError("no current runner configured.")
