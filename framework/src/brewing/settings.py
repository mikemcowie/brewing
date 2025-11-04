"""Application level settings."""

from __future__ import annotations
from contextvars import ContextVar, Token
from typing import Any
from dataclasses import dataclass, field
from brewing.db import Database, DatabaseConnectionConfiguration


_current: ContextVar[Settings[Any]] = ContextVar("current_settings")


class NoCurrentSettings(LookupError):
    """No settings object has been pushed."""


@dataclass
class Settings[DBConnT: DatabaseConnectionConfiguration]:
    """Application level settings."""

    database: Database[DBConnT]
    current_token: Token[Settings[Any]] | None = field(default=None, init=False)

    pass

    def __enter__(self):
        self.current_token = _current.set(self)
        return self

    def __exit__(self, *_):
        if self.current_token:
            _current.reset(self.current_token)

    @classmethod
    def current(cls):
        """Return the current settings instance."""
        if settings := _current.get():
            return settings
        raise NoCurrentSettings(
            "No current settings available. "
            "Push settings by constucting a Settings instance, i.e. "
            "with Settings(...):"
        )
