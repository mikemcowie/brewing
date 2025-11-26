"""Protocols and type declarations for the brewing.db package."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Protocol

if TYPE_CHECKING:
    from sqlalchemy.engine import URL

    from brewing.db.settings import DatabaseType


class DatabaseConnectionConfiguration(Protocol):
    """
    Protocol for loading database connections.

    Connections are expected to be loaded from environment variables
    per 12-factor principals, so no arguments are accepted in the constructor.
    """

    database_type: ClassVar[DatabaseType]

    def __init__(self): ...
    def url(self) -> URL:
        """Return the sqlalchemy URL for the database."""
        ...
