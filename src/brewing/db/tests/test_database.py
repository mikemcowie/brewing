from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text
from testing_samples import sample1

from brewing.db import Database, new_base, testing
from brewing.db.settings import DatabaseType, DBConfigurationError

if TYPE_CHECKING:
    from pytest_subtests import SubTests

Base = new_base()


def test_database_initializing_without_specifying_database_type(
    db_type: DatabaseType, running_db: None
):
    # Given the db type in the environment
    # If we initialize a database
    db = Database(base=Base)
    # We can get a configuration of the expect type
    assert db.config.database_type is db_type


def test_database_initializing_with_specifying_database_type(
    db_type: DatabaseType, running_db: None, subtests: SubTests
):
    with subtests.test("right-type"):
        db = Database(base=Base, db_type=db_type)
        assert db.config.database_type is db_type
    other_db_types = [t for t in DatabaseType if t is not db_type]
    for other_db_type in other_db_types:
        if {db_type, other_db_type} == {DatabaseType.mariadb, DatabaseType.mysql}:
            # Skip this check for mariadb and mysql which are close enough
            # that the environment variahles can connect to the other.
            continue
        with subtests.test(f"wromg-type-{other_db_type}"):
            db = Database(base=Base, db_type=other_db_type)
            with pytest.raises(DBConfigurationError):
                _ = db.config


@pytest.mark.asyncio
async def test_engine_cached(db_type: DatabaseType, running_db: None):
    dialect = db_type.dialect()
    db = Database(base=Base)
    assert db.engine is db.engine
    assert db.engine.url.drivername == f"{db_type.value}+{dialect.dialect_name}"


@pytest.mark.asyncio
async def test_connect_with_engine(db_sample_1: Database):
    async with db_sample_1.engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
    assert len(list(result)) == 1


def test_default_migrations_revisions_directory(
    db_type: DatabaseType, running_db: None
):
    db = Database(base=Base)
    assert (
        db.migrations.revisions_dir == (Path(__file__).parent / "revisions").resolve()
    )


@pytest.mark.asyncio
async def test_sample1(db_sample_1: Database):
    async with testing.upgraded(db_sample_1):
        await sample1.run_sample()
