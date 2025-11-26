from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import MetaData, text
from testing_samples import db_sample1

from brewing.db import Database, testing

if TYPE_CHECKING:
    from brewing.db.settings import DatabaseType


@pytest.mark.asyncio
async def test_engine_cached(db_type: DatabaseType, running_db: None):
    dialect = db_type.dialect()
    db = Database(metadata=MetaData(), config_type=dialect.connection_config_type)
    assert db.engine is db.engine
    assert db.engine.url.drivername == f"{db_type.value}+{dialect.dialect_name}"


@pytest.mark.asyncio
async def test_connect_with_engine(database_sample_1: Database):
    async with database_sample_1.engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
    assert len(list(result)) == 1


def test_default_migrations_revisions_directory(
    db_type: DatabaseType, running_db: None
):
    dialect = db_type.dialect()
    db = Database(metadata=MetaData(), config_type=dialect.connection_config_type)
    assert (
        db.migrations.revisions_dir == (Path(__file__).parent / "revisions").resolve()
    )


@pytest.mark.asyncio
async def test_sample1(database_sample_1: Database):
    async with testing.upgraded(database_sample_1):
        await db_sample1.run_sample(database_sample_1)
