"""Support for database migrations based on alembic."""

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine


class Migrations:
    """Controls migrations."""

    def __init__(self, engine: AsyncEngine, metadata: MetaData):
        self._engine = engine
        self._metadata = metadata
