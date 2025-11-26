"""Contextvars and functions to access them."""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from brewing import Brewing
    from brewing.db.types import DatabaseProtocol

## The actual contextvars are private here:
_CURRENT_APP: ContextVar[Brewing | None] = ContextVar("current_app", default=None)
_CURRENT_DB_SESSION: ContextVar[AsyncSession | None] = ContextVar(
    "current_session", default=None
)


class ContextNotAvailable(LookupError):
    """Raised attempting to load a context that is not available."""


def current_app() -> Brewing:
    """Get the current active brewing instance."""
    app = _CURRENT_APP.get()
    if not app:
        raise ContextNotAvailable("No current active brewing app.")
    return app


@contextmanager
def push_app(app: Brewing):
    """Set the given app as current, yielding and unsetting it when closed."""
    token = _CURRENT_APP.set(app)
    yield
    _CURRENT_APP.reset(token)


def current_database() -> DatabaseProtocol:
    """Return the database of the currently active brewing app."""
    return current_app().database


@asynccontextmanager
async def db_session():  ### TODO - make sure all db access is through this.
    db = current_database()
    if session := _CURRENT_DB_SESSION.get():
        yield session
        return
    async with db.session() as session:
        token = _CURRENT_DB_SESSION.set(session)
        yield session
        _CURRENT_DB_SESSION.reset(token)
        await session.commit()
