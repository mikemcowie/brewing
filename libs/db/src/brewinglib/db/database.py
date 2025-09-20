import functools
import inspect
from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager
from functools import cache, cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from brewinglib.cli import CLI
from brewinglib.db.migrate import Migrations, MigrationsConfig
from brewinglib.db.types import DatabaseConnectionConfiguration
from brewinglib.generic import runtime_generic
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

if not TYPE_CHECKING:
    create_async_engine = cache(create_async_engine)


def _find_calling_file(stack: list[inspect.FrameInfo]):
    for frameinfo in stack:
        if frameinfo.filename not in (__file__, functools.__file__):
            return Path(frameinfo.filename)
    raise RuntimeError("Could not find calling file.")


@runtime_generic
class Database[ConfigT: DatabaseConnectionConfiguration]:
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

    @cached_property
    def cli(self) -> CLI:
        return CLI("db", wraps=self.migrations)

    @cached_property
    def metadata(self) -> tuple[MetaData, ...]:
        return self._metadata

    @cached_property
    def migrations(self) -> Migrations:
        return Migrations(
            MigrationsConfig(
                engine=self.engine,
                metadata=self.metadata,
                revisions_dir=self._revisions_directory,
            )
        )

    @property
    def engine(self):
        return create_async_engine(url=self.config_type().url())

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        async with AsyncSession(bind=self.engine) as session:
            yield session
