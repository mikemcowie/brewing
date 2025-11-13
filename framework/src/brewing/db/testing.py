"""Database testing utilities."""

from __future__ import annotations

import asyncio
import os
from contextvars import ContextVar

from sqlalchemy_utils import create_database, database_exists
from dataclasses import dataclass
from collections.abc import Generator, MutableMapping
from contextlib import asynccontextmanager, contextmanager, AbstractContextManager
from functools import partial
from pathlib import Path
from itertools import count
import socket
from tempfile import TemporaryDirectory

from typing import TYPE_CHECKING, Protocol
import structlog
from brewing.db.settings import DatabaseType

if TYPE_CHECKING:
    from testcontainers.mysql import MySqlContainer
    from testcontainers.postgres import PostgresContainer
    from brewing.db.types import DatabaseProtocol


logger = structlog.get_logger()
iter_num = count()


def _find_free_port() -> int:
    sock = socket.socket()
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@contextmanager
def _compose(context: Path, compose_file: Path):
    from testcontainers.compose import DockerCompose

    with DockerCompose(
        context=context,
        compose_file_name=str(compose_file),
        keep_volumes=True,
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

    def __call__(self) -> AbstractContextManager[None]:
        """Generate test database."""
        ...


_current_pg: ContextVar[PostgresContainer | None] = ContextVar(
    "_current_pg", default=None
)
_current_mysql: ContextVar[MySqlContainer | None] = ContextVar(
    "_current_mysql", default=None
)
_current_mariadb: ContextVar[MySqlContainer | None] = ContextVar(
    "_current_mariadb", default=None
)


@contextmanager
def _postgresql():
    from testcontainers.postgres import PostgresContainer

    pg = _current_pg.get()
    enter_pg = noop()
    if not pg:
        pg = PostgresContainer()
        enter_pg = pg
    token = _current_pg.set(pg)
    dbname = f"testdb_{next(iter_num)}"

    with enter_pg:
        port = pg.get_exposed_port(pg.port)
        url = f"postgresql+psycopg://{pg.username}:{pg.password}@127.0.0.1:{port}/{dbname}"
        if not database_exists(url):
            create_database(url)
        with env(
            {
                "PGUSER": pg.username,
                "PGPASSWORD": pg.password,
                "PGPORT": str(port),
                "PGDATABASE": pg.dbname,
                "PGHOST": "127.0.0.1",
            }
        ):
            yield
            if enter_pg is pg:
                _current_pg.reset(token)


@contextmanager
def _postgresql_compose():
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
        ),
    ):
        yield


@contextmanager
def _sqlite():
    with (
        TemporaryDirectory(delete=False) as dir,
        env({"SQLITE_DATABASE": str(Path(dir) / "db.sqlite")}),
    ):
        yield


@contextmanager
def _mysql(
    image: str = "mysql:latest",
    contextvar: ContextVar[MySqlContainer | None] = _current_mysql,
):
    from testcontainers.mysql import MySqlContainer

    mysql = contextvar.get()
    enter = noop()
    if not mysql:
        mysql = MySqlContainer(image=image)
        enter = mysql
    token = contextvar.set(mysql)
    dbname = f"testdb_{next(iter_num)}"

    with enter:
        port = mysql.get_exposed_port(mysql.port)
        url = f"mysql://root:{mysql.root_password}@127.0.0.1:{port}/{dbname}"
        if not database_exists(url):
            create_database(url)
        with env(
            {
                "MYSQL_HOST": "127.0.0.1",
                "MYSQL_USER": "root",
                "MYSQL_PWD": mysql.root_password,
                "MYSQL_TCP_PORT": str(port),
                "MYSQL_DATABASE": dbname,
            }
        ):
            yield
            if enter is mysql:
                contextvar.reset(token)


@contextmanager
def _mysql_compose(image: str = "mysql:latest"):
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
        ),
    ):
        yield


mariadb = partial(_mysql, image="mariadb:latest", contextvar=_current_mariadb)
mariadb_compose = partial(_mysql_compose, image="mariadb:latest")


@dataclass
class _DatabaseTestImp:
    test: TestingDatabase
    dev: TestingDatabase


_TEST_DATABASE_IMPLEMENTATIONS: dict[DatabaseType, _DatabaseTestImp] = {
    DatabaseType.sqlite: _DatabaseTestImp(_sqlite, _sqlite),
    DatabaseType.postgresql: _DatabaseTestImp(_postgresql, _postgresql_compose),
    DatabaseType.mysql: _DatabaseTestImp(_mysql, _mysql_compose),
    DatabaseType.mariadb: _DatabaseTestImp(mariadb, mariadb),
}


@contextmanager
def noop(*_, **__) -> Generator[None, None, None]:  # type: ignore
    """Noop conextmanager."""
    yield


@contextmanager
def testing(db_type: DatabaseType):
    """Temporarily create and set environment variables for connection to given db type."""
    with _TEST_DATABASE_IMPLEMENTATIONS[db_type].test():
        yield


@contextmanager
def dev(db_type: DatabaseType):
    """Enter a dev database context with persistence."""
    with _TEST_DATABASE_IMPLEMENTATIONS[db_type].dev():
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
    await db.engine.dispose()


# make sure pytest doesn't try this
testing.__test__ = False  # type: ignore
