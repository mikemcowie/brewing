from __future__ import annotations

from typing import TYPE_CHECKING

from brewing.db import settings

if TYPE_CHECKING:
    from brewing.db.settings import DatabaseType


def test_db_types_to_dialects_is_exhaustive(db_type: DatabaseType):
    assert isinstance(db_type.dialect(), settings.Dialect)
