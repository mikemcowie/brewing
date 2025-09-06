from pathlib import Path
from unittest.mock import MagicMock

from cauldron_incubator.db.database import Migrations


def test_migrations_path_loading():
    with_file_string = Migrations(MagicMock(), __file__)
    with_file_path = Migrations(MagicMock(), Path(__file__))
    with_dir_string = Migrations(MagicMock(), str(Path(__file__).parent))
    with_dir_path = Migrations(MagicMock(), Path(__file__).parent)
    options = [with_dir_path, with_dir_string, with_file_path, with_file_string]

    for option in options:
        assert option.migration_config().get_version_locations_list() == [
            str(Path(__file__).parent / "versions")
        ]
