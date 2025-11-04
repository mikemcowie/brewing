"""Database testing utilities."""

from __future__ import annotations

import asyncio
import os

from collections.abc import Generator, MutableMapping
from contextlib import AbstractContextManager, asynccontextmanager, contextmanager
from functools import partial
from pathlib import Path
import socket

from typing import TYPE_CHECKING, Protocol
import structlog
from brewing.db.settings import DatabaseType
from testcontainers.compose import DockerCompose

if TYPE_CHECKING:
    from brewing.db.types import DatabaseProtocol


logger = structlog.get_logger()


def _find_free_port() -> int:
    sock = socket.socket()
    sock.bind(("", 0))
    return sock.getsockname()[1]


@contextmanager
def _compose(context: Path, compose_file: Path, persist_data: bool):
    with DockerCompose(
        context=context,
        compose_file_name=str(compose_file),
        keep_volumes=persist_data,
        wait=True,
    ):
        yield


@contextmanager
def persistent_volume(base_path: Path, name: str | None = None):
    """Provision persistent storage for container."""
    if not name:
        yield None
        return
    yield base_path / name


@contextmanager
def env(
    new_env: dict[str, str], environ: MutableMapping[str, str] = os.environ
) -> Generator[None]:
    """Temporarily modify environment (or other provided mapping), restore original values on cleanup."""
    orig: dict[str, str | None] = {}
    for key, value in new_env.items():
        orig[key] = environ.get(key)
        environ[key] = value
    yield
    # Cleanup - restore the original values
    # or delete if they weren't set.
    for key, value in orig.items():
        if value is None:
            del environ[key]
        else:
            environ[key] = value


class TestingDatabase(Protocol):
    """Protocol for running a dev or test database."""

    def __call__(self, persist_data: bool) -> AbstractContextManager[None]:
        """Generate test database with storage at path."""
        ...


@contextmanager
def _postgresql(persist_data: bool):
    port = _find_free_port()
    with (
        env(
            {
                "PGHOST": "127.0.0.1",
                "PGPORT": str(port),
                "PGDATABASE": "test",
                "PGUSER": "test",
                "PGPASSWORD": "test",
            }
        ),
        _compose(
            context=Path(__file__).parent,
            compose_file=Path(__file__).parent / "compose" / "compose.postgresql.yaml",
            persist_data=persist_data,
        ),
    ):
        yield


@contextmanager
def _sqlite(persist_data: bool):
    db = str(Path.cwd() / "db.sqlite") if persist_data else ":memory:"
    with env({"SQLITE_DATABASE": db}):
        yield


@contextmanager
def _mysql(persist_data: bool, image: str = "mysql:latest"):
    port = _find_free_port()
    with (
        env(
            {
                "MYSQL_HOST": "127.0.0.1",
                "MYSQL_USER": "test",
                "MYSQL_PWD": "test",
                "MYSQL_TCP_PORT": str(port),
                "MYSQL_DATABASE": "test",
                "IMAGE": image,
            }
        ),
        _compose(
            context=Path(__file__).parent,
            compose_file=Path(__file__).parent / "compose" / "compose.mysql.yaml",
            persist_data=persist_data,
        ),
    ):
        yield


mariadb = partial(_mysql, image="mariadb:latest")


_TEST_DATABASE_IMPLEMENTATIONS: dict[DatabaseType, TestingDatabase] = {
    DatabaseType.sqlite: _sqlite,
    DatabaseType.postgresql: _postgresql,
    DatabaseType.mysql: _mysql,
    DatabaseType.mariadb: mariadb,
}


@contextmanager
def noop():  # type: ignore
    """Noop conextmanager."""
    yield


@contextmanager
def testing(db_type: DatabaseType, persist_data: bool):
    """Temporarily create and set environment variables for connection to given db type."""
    with _TEST_DATABASE_IMPLEMENTATIONS[db_type](persist_data=persist_data):
        yield


@asynccontextmanager
async def upgraded(db: DatabaseProtocol):
    """Temporarily deploys tables for given database, dropping them in cleanup phase."""
    async with db.engine.begin() as conn:
        for metadata in db.metadata:
            await conn.run_sync(metadata.create_all)
            asyncio.get_running_loop().run_in_executor(
                None, db.migrations.stamp, "head"
            )

    yield
    async with db.engine.begin() as conn:
        for metadata in db.metadata:
            await conn.run_sync(metadata.drop_all)


# make sure pytest doesn't try this
testing.__test__ = False  # type: ignore
