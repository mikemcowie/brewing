"""Settings classes for different database types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto
from typing import TYPE_CHECKING, ClassVar

from frozendict import frozendict
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

from brewing.db.types import DatabaseConnectionConfiguration

if TYPE_CHECKING:
    from collections.abc import Mapping


class DatabaseType(StrEnum):
    """Supported database names."""

    sqlite = auto()
    postgresql = auto()
    mysql = auto()
    mariadb = auto()

    def dialect(self) -> Dialect:
        """Return dialect object associated with the given type."""
        return _DATABASE_TYPE_TO_DIALECT[self]


@dataclass(frozen=True)
class Dialect:
    """Collection of data associated with a given database type."""

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
    """Provide the sqlalchemy URL for given inputs."""
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
    """Common base class for db settings."""

    model_config = SettingsConfigDict(frozen=True)


class SQLiteSettings(OurBaseSettings):
    """Connection settings for sqlite."""

    if TYPE_CHECKING:

        def __init__(self):
            return None

    database_type: ClassVar = DatabaseType.sqlite
    SQLITE_DATABASE: str

    def url(self):
        """Provide url for instance."""
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
    """Connection settings for postgresql."""

    if TYPE_CHECKING:

        def __init__(self):
            return None

    model_config = SettingsConfigDict(frozen=True)

    database_type: ClassVar = DatabaseType.postgresql
    PGHOST: str
    PGPORT: int
    PGUSER: str
    PGPASSWORD: str
    PGDATABASE: str

    def url(self):
        """Provide url for instance."""
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
    """Connection settings for mysql."""

    dialect: ClassVar = DatabaseType.mysql
    if TYPE_CHECKING:

        def __init__(self):
            return None

    database_type: ClassVar = DatabaseType.mysql
    MYSQL_USER: str
    MYSQL_PWD: str
    MYSQL_HOST: str
    MYSQL_TCP_PORT: int
    MYSQL_DATABASE: str

    def url(self):
        """Provide url for instance."""
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
    """Connection settings for mariadb."""

    dialect: ClassVar = DatabaseType.mariadb
    database_type: ClassVar = DatabaseType.mariadb
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
