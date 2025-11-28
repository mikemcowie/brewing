"""Utilities supporting the db module."""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import inspect


def find_calling_frame(stack: list[inspect.FrameInfo], exclude_file: str):
    """Find where a function was called from,"""
    for frameinfo in stack:
        if (
            frameinfo.filename not in (__file__, functools.__file__, exclude_file)
            and ".py" in frameinfo.filename
        ):
            return frameinfo
    raise RuntimeError("Could not find calling file.")
