from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto
from typing import TYPE_CHECKING, ClassVar

from frozendict import frozendict
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

if TYPE_CHECKING:
    from collections.abc import Mapping

    from brewinglib.db.types import DatabaseConnectionConfiguration


class DatabaseType(StrEnum):
    sqlite = auto()
    postgresql = auto()
    mysql = auto()
    mariadb = auto()

    def dialect(self) -> Dialect:
        return _DATABASE_TYPE_TO_DIALECT[self]


@dataclass(frozen=True)
class Dialect:
    database_type: DatabaseType
    package: str
    dialect_name: str
    connection_config_type: type[DatabaseConnectionConfiguration]


def load_url(  # noqa: PLR0913
    db_type: DatabaseType,
    *,
    username: str | None,
    password: str | None,
    host: str | None,
    port: int | None,
    database: str | None,
    query: Mapping[str, tuple[str, ...] | str] | None,
) -> URL:
    dialect = db_type.dialect()
    return URL(
        f"{db_type.value}+{dialect.dialect_name}",
        username,
        password,
        host,
        port,
        database,
        frozendict(query or {}),  # type: ignore
    )


class OurBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(frozen=True)


class SQLiteSettings(OurBaseSettings):
    if TYPE_CHECKING:

        def __init__(self):
            return None

    SQLITE_DATABASE: str

    def url(self):
        return load_url(
            DatabaseType.sqlite,
            username=None,
            password=None,
            host=None,
            port=None,
            database=self.SQLITE_DATABASE,
            query={},
        )


class PostgresqlSettings(OurBaseSettings):
    if TYPE_CHECKING:

        def __init__(self):
            return None

    model_config = SettingsConfigDict(frozen=True)

    PGHOST: str
    PGPORT: int
    PGUSER: str
    PGPASSWORD: str
    PGDATABASE: str

    def url(self):
        return load_url(
            DatabaseType.postgresql,
            username=self.PGUSER,
            password=self.PGPASSWORD,
            host=self.PGHOST,
            port=self.PGPORT,
            database=self.PGDATABASE,
            query={},
        )


class MySQLSettings(OurBaseSettings):
    dialect: ClassVar = DatabaseType.mysql
    if TYPE_CHECKING:

        def __init__(self):
            return None

    MYSQL_USER: str
    MYSQL_PWD: str
    MYSQL_HOST: str
    MYSQL_TCP_PORT: int
    MYSQL_DATABASE: str

    def url(self):
        return load_url(
            self.dialect,
            username=self.MYSQL_USER,
            password=self.MYSQL_PWD,
            host=self.MYSQL_HOST,
            port=self.MYSQL_TCP_PORT,
            database=self.MYSQL_DATABASE,
            query={},
        )


class MariaDBSettings(MySQLSettings):
    dialect: ClassVar = DatabaseType.mariadb
    if TYPE_CHECKING:

        def __init__(self):
            return None


# fmt: off
_DATABASE_TYPE_TO_DIALECT = {
DatabaseType.sqlite:     Dialect( DatabaseType.sqlite,     "aiosqlite", "aiosqlite", SQLiteSettings     ),
DatabaseType.postgresql: Dialect( DatabaseType.postgresql, "psycopg",   "psycopg",   PostgresqlSettings ),
DatabaseType.mysql:      Dialect( DatabaseType.mysql,      "aiomysql",  "aiomysql",  MySQLSettings      ),
DatabaseType.mariadb:    Dialect( DatabaseType.mariadb,    "aiomysql",  "aiomysql",  MariaDBSettings    ),
}
# fmt: on
