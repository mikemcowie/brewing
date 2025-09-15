from pathlib import Path

from brewinglib.db.migrate import Migrations
from brewinglib.db.types import DatabaseProtocol


def test_generate_migration(database_sample_1: DatabaseProtocol, tmp_path: Path):
    Migrations(
        engine=database_sample_1.engine,
        metadata=database_sample_1.metadata,
        migrations_dir=Path(__file__).parent / "migrations",
        revisions_dir=tmp_path / "revisions",
    )
