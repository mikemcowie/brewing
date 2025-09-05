from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from alembic import command
from alembic.config import Config
from fastapi import Depends
from fastapi import Request as _Request
from pydantic.alias_generators import to_snake
from sqlalchemy import DateTime, MetaData, func, text
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.engine import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    MappedColumn,
    Session,
    declared_attr,
    mapped_column,
)

from project_manager import migrations
from project_manager.settings import Settings

Request = _Request  # So that ruff won't hide it behind type checking
MIGRATIONS_DIR = Path(migrations.__file__).parent.resolve()
VERSIONS_DIR = MIGRATIONS_DIR / "versions"
# keyword args for engine creation, which are written to be overwritten for tests
ASYNC_ENGINE_KWARGS: dict[str, Any] = {}
SYNC_ENGINE_KWARGS: dict[str, Any] = {}


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator
    from datetime import datetime
    from uuid import UUID

    _engine = create_engine
    _async_engine = create_async_engine
else:

    @cache
    def _engine(*args, **kwargs):
        return create_engine(*args, **kwargs | SYNC_ENGINE_KWARGS)

    @cache
    def _async_engine(*args, **kwargs):
        return create_async_engine(*args, **kwargs | ASYNC_ENGINE_KWARGS)


metadata = MetaData()


class Base(DeclarativeBase):
    __abstract__ = True
    metadata = metadata

    @declared_attr  # type: ignore
    def __tablename__(cls) -> str:  # noqa: N805
        return to_snake(cls.__name__)


class Database:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.async_engine = _async_engine(url=self.build_uri("asyncpg"))
        self.sync_engine = _engine(url=self.build_uri("psycopg"))
        self.load_models()
        self.metadata = metadata

    def load_models(self) -> None:
        # ruff: noqa: F401,PLC0415
        import project_manager.organizations.models
        import project_manager.resources.models
        import project_manager.users

    def build_uri(self, driver: str) -> str:
        return f"postgresql+{driver}://{self.settings.PGUSER}:{self.settings.PGPASSWORD.get_secret_value()}@{self.settings.PGHOST}:{self.settings.PGPORT}/{self.settings.PGDATABASE}"

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


def uuid_primary_key() -> MappedColumn[UUID]:
    return mapped_column(
        pg.UUID,
        default=None,
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )


def created_field() -> MappedColumn[datetime]:
    return mapped_column(
        DateTime(timezone=True), default=None, index=True, server_default=func.now()
    )


def updated_field() -> MappedColumn[datetime]:
    return mapped_column(
        DateTime(timezone=True),
        default=None,
        index=True,
        server_default=func.now(),
        onupdate=func.now(),
    )


def deleted_field() -> MappedColumn[datetime]:
    return mapped_column(
        DateTime(timezone=True), default=None, index=True, nullable=True
    )


async def db_session(request: Request) -> AsyncGenerator[AsyncSession, Any]:
    from project_manager.application import Application

    assert isinstance(request.app.project_manager, Application)
    async with request.app.project_manager.database.session() as session:
        yield session
