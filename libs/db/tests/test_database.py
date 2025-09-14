import pytest
from brewinglib.db import Database
from brewinglib.db.settings import DatabaseType
from brewinglib.db.types import DatabaseProtocol
from sqlalchemy import text


def test_engine_cached(db_type: DatabaseType, running_db: None):
    dialect = db_type.dialect()
    db1 = Database[dialect.connection_config_type]()
    db2 = Database[dialect.connection_config_type]()
    assert db1.engine is db2.engine
    assert db1.engine.url.drivername == f"{db_type.value}+{dialect.dialect_name}"


@pytest.mark.asyncio
async def test_connect_with_engine(database: DatabaseProtocol):
    async with database.engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
    assert len(list(result)) == 1
