"""Processors: load data structures prior to endpoint function, and render them after.

Processors are where Brewing adds extra functionality on top of fastapi to expand
the options availanble at endpoint functions.
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Protocol, Self

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from brewing.http.serialization.negotiation import Negotiator


@dataclass
class Processors[InputT, InternalT, OutputT]:
    """Hold the loader and renderer(s) for each function."""

    negotiator: Negotiator
    loader: Loader[InputT, InternalT]
    renderer: Iterable[Renderer[InternalT, OutputT]]

    def __post_init__(self):
        if len(set(self.renderer)) < len(list(self.renderer)):
            raise RuntimeError(
                "Invalid renderers: 2 were provided with same content type.",
                {"renderers": self.renderer},
            )

    def load(self, obj: InputT, /) -> InternalT:
        return self.loader(obj)

    def render(self, obj: InternalT, accepts: str, /) -> OutputT:
        return self.negotiator.select(accepts, self.renderer)(obj)


class Loader[InputT, InternalT](Protocol):
    """Convert an object from the form fastapi loaded from the request, into the form annotated on the endpoint."""

    @abstractmethod
    def __call__(self, obj: InputT, /) -> InternalT:
        """Convert object from fastapi-received form to internal form."""
        ...


class Renderer[InternalT, OutputT](Protocol):
    """Convert the application's internal representation of a resource to the form fastapi will return."""

    content_type: ClassVar[str]

    def __iter__(self) -> Iterator[Self]:
        """Iterate over the renderer, yielding self."""
        return iter((self,))

    @abstractmethod
    def __call__(self, obj: InternalT, /) -> OutputT:
        """Convert object from internal form output form.."""
        ...
