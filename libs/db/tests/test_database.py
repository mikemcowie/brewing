from brewinglib.db.database import Database
from brewinglib.db.types import DatabaseType


def test_engine_cached(db_type: DatabaseType, running_db: None):
    dialect = db_type.dialect()
    db1 = Database[dialect.connection_config_type]()
    db2 = Database[dialect.connection_config_type]()
    assert db1.engine is db2.engine
    assert db1.engine.url.drivername == f"{db_type.value}+{dialect.dialect_name}"
