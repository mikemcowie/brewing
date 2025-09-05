from __future__ import annotations

from contextlib import asynccontextmanager
from functools import cache, cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

from alembic import command
from alembic.config import Config
from project_manager import migrations
from runtime_generic import runtime_generic
from sqlalchemy.engine import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from cauldron.db.base import metadata
from cauldron.db.settings import DBSettingsType
from cauldron.http import Request as _Request

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


@runtime_generic
class Database[SettingsT: DBSettingsType]:
    settings_cls: type[SettingsT]

    @cached_property
    def metadata(self):
        return metadata

    @cached_property
    def settings(self):
        return self.settings_cls()

    @cached_property
    def async_engine(self):
        return _async_engine(url=self.settings.uri(use_async=True))

    @cached_property
    def sync_engine(self):
        return _engine(url=self.settings.uri(use_async=False))

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, Any]:
        async with AsyncSession(bind=self.async_engine, expire_on_commit=False) as sess:
            yield sess

    def migration_config(self) -> Config:
        config = Config()
        config.set_main_option("script_location", "project_manager:migrations")
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
            rev_id=f"{len(list(VERSIONS_DIR.glob('*.py'))):05d}",
            message=message,
            autogenerate=autogenerate,
        )
