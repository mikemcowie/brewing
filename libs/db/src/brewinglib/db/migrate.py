"""Support for database migrations based on alembic."""

from __future__ import annotations

import contextlib
from contextvars import ContextVar
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

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
    metadata: MetaData
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


_current_config: ContextVar[MigrationsConfig] = ContextVar("current_config")


@contextlib.contextmanager
def set_config(config: MigrationsConfig):
    token = _current_config.set(config)
    yield
    _current_config.reset(token)


def current_config():
    return _current_config.get()


class Migrations:
    """Controls migrations."""

    def __init__(self, config: MigrationsConfig):
        self._config = config

    def generate_revision(self, message: str, autogenerate: bool):
        with set_config(self._config):
            command.revision(
                self._config.alembic,
                rev_id=f"{len(list(self._config.revisions_dir.glob('*.py'))):05d}",
                message=message,
                autogenerate=autogenerate,
            )

    def upgrade(self, revision: str = "head"):
        with set_config(self._config):
            command.upgrade(self._config.alembic, revision=revision)

    def downgrade(self, revision: str):
        with set_config(self._config):
            command.downgrade(self._config.alembic, revision=revision)
