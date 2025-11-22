"""Manages the global contextvars for brewing."""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, ClassVar, Self

if TYPE_CHECKING:
    from collections.abc import Generator, MutableMapping


class HasGlobalContext:
    """Mixin class that adds a class variable containing the "current" instance"""

    current: ClassVar[ContextVar[Self | None]] = ContextVar(
        "contextholding", default=None
    )

    def __init_subclass__(cls, *args: Any, **kwargs: Any) -> None:
        cls.current = ContextVar(cls.__name__, default=None)
        super().__init_subclass__(*args, **kwargs)


class ContextNotAvailable(LookupError):
    """Raised attempting to load a context that is not available."""


def current(cls: type[HasGlobalContext]):
    if result := cls.current.get():
        return result
    raise ContextNotAvailable(
        f"No current instance of {cls=!s} is available. "
        f"It needs to be loaded with {__name__}.{push.__name__}(instance)"
    )


@contextmanager
def push(*instance: HasGlobalContext):
    """Push the context of some object."""
    tokens = [i.__class__.current.set(i) for i in instance]
    yield
    [
        i.__class__.current.reset(token)
        for i, token in zip(instance, tokens, strict=True)
    ]


@contextmanager
def env(
    new_env: dict[str, str], environ: MutableMapping[str, str] = os.environ
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
