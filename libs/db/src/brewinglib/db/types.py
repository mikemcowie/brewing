from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto


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


_DATABASE_TYPE_TO_DIALECT = {
    DatabaseType.sqlite: Dialect(DatabaseType.sqlite, "aiosqlite", "aiosqlite"),
    DatabaseType.postgresql: Dialect(DatabaseType.postgresql, "psycopg", "psygopg"),
    DatabaseType.mysql: Dialect(DatabaseType.mysql, "aiomysql", "aiomysql"),
    DatabaseType.mariadb: Dialect(DatabaseType.mysql, "aiomysql", "aiomysql"),
}
