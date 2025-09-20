"""Support for database migrations based on alembic."""

from __future__ import annotations

import contextlib
from contextvars import ContextVar
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, overload

from alembic import command
from alembic.config import Config as AlembicConfig

if TYPE_CHECKING:
    from sqlalchemy import MetaData
    from sqlalchemy.ext.asyncio import AsyncEngine

type MigrationsDir = Path
type RevisionsDir = Path


class MigrationsConfigError(RuntimeError):
    """raised for invalid migrations config states."""


@dataclass(frozen=True, kw_only=True)
class MigrationsConfig:
    engine: AsyncEngine
    metadata: MetaData | tuple[MetaData, ...]
    migrations_dir: MigrationsDir = Path(__file__).parent / "migrations"
    revisions_dir: RevisionsDir

    @cached_property
    def alembic(self) -> AlembicConfig:
        config = AlembicConfig()
        if not self.migrations_dir.is_dir():
            raise MigrationsConfigError(
                f"path {self.migrations_dir!s} is not a valid directory."
            )
        if not self.revisions_dir.is_dir():
            raise MigrationsConfigError(
                f"path {self.revisions_dir!s} is not a valid directory."
            )
        config.set_main_option("script_location", str(self.migrations_dir))
        config.set_main_option("version_locations", str(self.revisions_dir))
        config.set_main_option("path_separator", ";")
        config.set_main_option("file_template", "rev_%%(rev)s_%%(slug)s")
        return config


### Begin configuration machery for alembic context
# This is basically working around the challenge of being hard to otherwise
# call the machinery in env.py with parameters.
# instead we use a contextvar, and `set_config` contextmanager to set the value
# before alembic gets invoked, removing it after.

# configvar itself is private, as the 2 functions below it are the interface to it.
_current_config: ContextVar[MigrationsConfig] = ContextVar("current_config")


@contextlib.contextmanager
def set_config(config: MigrationsConfig):
    token = _current_config.set(config)
    yield
    _current_config.reset(token)


_NO_DEFAULT = object()


@overload
def current_config() -> MigrationsConfig: ...
@overload
def current_config[DefaultT](default: DefaultT) -> DefaultT | MigrationsConfig: ...


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

    @property
    def config(self):
        return self._config

    def generate_revision(self, message: str, autogenerate: bool):
        """Generate a new migration."""
        with set_config(self._config):
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
