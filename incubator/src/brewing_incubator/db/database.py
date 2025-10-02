from __future__ import annotations

from contextlib import asynccontextmanager
from functools import cache, cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from alembic import command
from alembic.config import Config
from brewing.generic import runtime_generic
from sqlalchemy.engine import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from brewing_incubator.db import migrations
from brewing_incubator.db.settings import DBSettingsType
from brewing_incubator.http import Request as _Request

Request = _Request  # So that ruff won't hide it behind type checking

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


MIGRATIONS_DIR = Path(migrations.__file__).parent.resolve()
VERSIONS_DIR = MIGRATIONS_DIR / "versions"
# keyword args for engine creation, which are written to be overwritten for tests
ASYNC_ENGINE_KWARGS: dict[str, Any] = {}
SYNC_ENGINE_KWARGS: dict[str, Any] = {}


if TYPE_CHECKING:
    _engine = create_engine
    _async_engine = create_async_engine
else:

    @cache
    def _engine(*args, **kwargs):
        return create_engine(*args, **kwargs | SYNC_ENGINE_KWARGS)

    @cache
    def _async_engine(*args, **kwargs):
        return create_async_engine(*args, **kwargs | ASYNC_ENGINE_KWARGS)


class MigrationsProtocol(Protocol):
    def upgrade(self, revision: str = "head") -> None: ...

    def downgrade(self, revision: str = "-1") -> None: ...

    def stamp(self, revision: str = "head") -> None: ...

    def create_revision(self, message: str, autogenerate: bool) -> None: ...


class Migrations[SettingsT: DBSettingsType]:
    """brewing's wrapper of alembic migrations.

    We use brewing-managed env.py, with a versions directory in the client package,
    declared programatically as part of the instantiation
    """

    def __init__(
        self,
        database: Database[SettingsT],
        versions_relative_to: Path | str,
        /,
        versions_directory: str | Path = "versions",
    ):
        self._database = database
        # The caller can simply instantiate via Migrations(__file__)
        # since we handle the case where it's a file by switching to
        # its parent
        if not isinstance(versions_relative_to, Path):
            versions_relative_to = Path(versions_relative_to)
        if versions_relative_to.is_file():
            versions_relative_to = versions_relative_to.parent
        self._versions_directory = (
            versions_relative_to / versions_directory
            if isinstance(versions_directory, str)
            else versions_directory.resolve()
        )

    def migration_config(self) -> Config:
        config = Config()
        config.set_main_option(
            "script_location", str(Path(__file__).parent / "migrations")
        )
        config.set_main_option("version_locations", str(self._versions_directory))
        return config

    def upgrade(self, revision: str = "head") -> None:
        command.upgrade(self.migration_config(), revision=revision, sql=False)

    def downgrade(self, revision: str = "-1") -> None:
        command.downgrade(self.migration_config(), revision=revision, sql=False)

    def stamp(self, revision: str = "head") -> None:
        command.stamp(self.migration_config(), revision=revision)

    def create_revision(self, message: str, autogenerate: bool) -> None:
        command.revision(
            self.migration_config(),
            rev_id=f"{len(list(self._versions_directory.glob('*.py'))):05d}",
            message=message,
            autogenerate=autogenerate,
        )


@runtime_generic
class Database[SettingsT: DBSettingsType]:
    settings_cls: type[SettingsT]

    @cached_property
    def settings(self):
        return self.settings_cls()

    @cached_property
    def async_engine(self):
        return _async_engine(url=self.settings.uri())

    @cached_property
    def sync_engine(self):
        return _engine(url=self.settings.uri())

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, Any]:
        async with AsyncSession(bind=self.async_engine, expire_on_commit=False) as sess:
            yield sess
