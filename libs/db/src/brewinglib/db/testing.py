from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, ClassVar

from brewinglib.db.types import DatabaseType

if TYPE_CHECKING:
    from types import TracebackType


class TestingDatabase:
    db_type: DatabaseType
    implementations: ClassVar[dict[DatabaseType, type[TestingDatabase]]] = {}

    def __init_subclass__(cls, db_type: DatabaseType) -> None:
        cls.db_type = db_type
        if implementation := TestingDatabase.implementations.get(db_type):
            raise RuntimeError(
                f"Cannot register test database class for {db_type=}; "
                f"{implementation=} is already registered"
            )
        TestingDatabase.implementations[db_type] = cls

    @abstractmethod
    def __init__(self):
        """Initialize the testingdatabase class."""

    @abstractmethod
    def __enter__(self):
        """Configure the database"""

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ):
        """cleanup the database"""


class TestingSQLite(TestingDatabase, db_type=DatabaseType.sqlite):
    pass


class TestingPostgresql(TestingDatabase, db_type=DatabaseType.postgresql):
    pass


class TestingMySQL(TestingDatabase, db_type=DatabaseType.mysql):
    pass


class TestingMariaDB(TestingDatabase, db_type=DatabaseType.mariadb):
    pass
