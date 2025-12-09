"""Processors: load data structures prior to endpoint function, and render them after.

Processors are where Brewing adds extra functionality on top of fastapi to expand
the options availanble at endpoint functions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, Self, final

if TYPE_CHECKING:
    from collections.abc import Iterator


class Renderer[InternalT, OutputT](ABC):
    """Convert the application's internal representation of a resource to the form fastapi will return."""

    content_type: ClassVar[str]

    @final
    def __iter__(self) -> Iterator[Self]:
        """Iterate over the renderer, yielding self.

        Being an iterable yielding itself allows us to simplify
        type hinting and runtime logic, as we're allowed to  pass
        exactly one renderer and it still can be iterated over just
        like a Seequence of renderers.
        """
        return iter((self,))

    @abstractmethod
    def __call__(self, obj: InternalT, /) -> OutputT:
        """Convert object from internal form output form.."""
        ...
