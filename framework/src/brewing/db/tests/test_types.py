from brewing.db import settings
from brewing.db.settings import DatabaseType


def test_db_types_to_dialects_is_exhaustive(db_type: DatabaseType):
    assert isinstance(db_type.dialect(), settings.Dialect)
