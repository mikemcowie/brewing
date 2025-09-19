from pathlib import Path

from brewinglib.db.migrate import Migrations, MigrationsConfig
from brewinglib.db.types import DatabaseProtocol


def test_generate_migration_without_autogenerate(
    database_sample_1: DatabaseProtocol, tmp_path: Path
):
    # Given migrations instance
    config = MigrationsConfig(
        engine=database_sample_1.engine,
        metadata=database_sample_1.metadata,
        revisions_dir=tmp_path / "revisions",
    )
    migrations = Migrations(config)
    config.revisions_dir.mkdir()
    # If we call generate
    migrations.generate_revision("gen 1", autogenerate=False)
    # then there will be a file generated in the revisions dir
    revisions_files = list(config.revisions_dir.glob("*.py"))
    assert len(revisions_files) == 1
    assert revisions_files[0].name == "rev_00000_gen_1.py"
