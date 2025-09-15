from brewinglib.db.migrations import Migrations
from brewinglib.db.types import DatabaseProtocol


def test_generate_migration(database_sample_1: DatabaseProtocol):
    Migrations(engine=database_sample_1.engine, metadata=database_sample_1.metadata)
