"""Utilities related to serializing/deserializing objects."""

from __future__ import annotations

from functools import cached_property
from typing import Any, cast


class ExcludeCachedProperty:
    """Mixin where cached_property attributes are excluded from __getstate__.

    This helps such objects be easier to pickle, as it allow unpickleable
    attributes to not prevent the object being pickleable.
    """

    def __getstate__(self) -> dict[str, Any]:
        state = cast("dict[str,Any]", super().__getstate__() or self.__dict__)
        if not isinstance(state, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(
                f"Cannot use {self.__getstate__.__class__} when __getstate__ "
                "returns an object with type other than None or a dict."
            )
        state = state.copy()  # Make sure we don't actually modify the instabnce dict.
        for key in (
            k
            for k in dir(self.__class__)
            if isinstance(getattr(self.__class__, k), cached_property)
        ):
            state.pop(key, None)
        return state
