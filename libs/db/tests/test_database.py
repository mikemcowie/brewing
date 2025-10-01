from pathlib import Path

import pytest
from brewinglib.db import Database, testing
from brewinglib.db.settings import DatabaseType
from brewinglib.db.types import DatabaseProtocol
from sqlalchemy import MetaData, text
from testing_samples import db_sample1


def test_engine_cached(db_type: DatabaseType, running_db: None):
    dialect = db_type.dialect()
    db1 = Database[dialect.connection_config_type](MetaData())
    db2 = Database[dialect.connection_config_type](MetaData())
    assert db1.engine is db2.engine
    assert db1.engine.url.drivername == f"{db_type.value}+{dialect.dialect_name}"


@pytest.mark.asyncio
async def test_connect_with_engine(database_sample_1: DatabaseProtocol):
    async with database_sample_1.engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
    assert len(list(result)) == 1


def test_default_migrations_revisions_directory(
    db_type: DatabaseType, running_db: None
):
    dialect = db_type.dialect()
    db = Database[dialect.connection_config_type](MetaData())
    assert (
        db.migrations.revisions_dir == (Path(__file__).parent / "revisions").resolve()
    )


@pytest.mark.asyncio
async def test_sample1(database_sample_1: DatabaseProtocol):
    async with testing.upgraded(database_sample_1):
        await db_sample1.run_sample(database_sample_1)
