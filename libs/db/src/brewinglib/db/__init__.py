"""Database helper package."""

from .base import new_base as new_base
from .database import Database as Database

__all__ = ["Database", "new_base"]
