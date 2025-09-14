from brewinglib.db import types


def test_db_types_to_dialects_is_exhaustive(db_type: types.DatabaseType):
    assert isinstance(db_type.dialect(), types.Dialect)
