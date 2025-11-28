"""Contextvars and functions to access them."""

from __future__ import annotations

import base64
import os
import pickle
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator, MutableMapping

    from brewing import Brewing
    from brewing.db import Database


_CURRENT_APP: ContextVar[Brewing | None] = ContextVar("current_app", default=None)

CURRENT_APP_BYTES_ENV = "CURRENT_APP_BYTES"


class ContextNotAvailable(LookupError):
    """Raised attempting to load a context that is not available."""


def current_app() -> Brewing:
    """Get the current active brewing instance."""
    if app := _CURRENT_APP.get():
        return app
    if app_bytes := os.environ.get(CURRENT_APP_BYTES_ENV):
        app = pickle.loads(base64.b64decode(app_bytes.encode()))
        _CURRENT_APP.set(app)
        return app
    else:
        raise ContextNotAvailable("No current active brewing app.")


@contextmanager
def push_app(app: Brewing):
    """Set the given app as current, yielding and unsetting it when closed."""
    token = _CURRENT_APP.set(app)
    with env({CURRENT_APP_BYTES_ENV: base64.b64encode(pickle.dumps(app)).decode()}):
        yield
    _CURRENT_APP.reset(token)


def current_database() -> Database:
    """Return the database of the currently active brewing app."""
    return current_app().database


@contextmanager
def env(
    new_env: MutableMapping[str, str], environ: MutableMapping[str, str] = os.environ
) -> Generator[None]:
    """Temporarily modify environment (or other provided mapping), restore original values on cleanup."""
    orig: dict[str, str | None] = {}
    for key, value in new_env.items():
        orig[key] = environ.get(key)
        environ[key] = value
    yield
    # Cleanup - restore the original values
    # or delete if they weren't set.
    for key, value in orig.items():
        if value is None:
            del environ[key]
        else:
            environ[key] = value
