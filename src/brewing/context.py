"""Manages the global contextvars for brewing."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, ClassVar, Self


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
