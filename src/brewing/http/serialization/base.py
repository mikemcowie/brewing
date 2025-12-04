"""Processors: load data structures prior to endpoint function, and render them after.

Processors are where Brewing adds extra functionality on top of fastapi to expand
the options availanble at endpoint functions.
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, Self

import pytest
from fastapi import HTTPException, status

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


@dataclass
class Processors[InputT, InternalT, OutputT]:
    """Hold the loader and renderer(s) for each function."""

    negotiator: Negotiator
    loader: Loader[InputT, InternalT]
    renderer: Iterable[Renderer[InternalT, OutputT]]

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


class NotAcceptable(HTTPException):
    """Content negotiation has failed."""

    status_code = status.HTTP_406_NOT_ACCEPTABLE

    def __init__(
        self,
        status_code: int | None = None,
        detail: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code or self.status_code
        super().__init__(self.status_code, detail, headers)


class Negotiator(Protocol):
    """Determine the renderer to use among an available set."""

    @abstractmethod
    def select(
        self, accepts: str, renderers: Iterable[Renderer[Any, Any]]
    ) -> Renderer[Any, Any]: ...


class TestNegotiation:
    def renderer_caller(self):
        def _func(obj: object):
            return obj

        return _func

    def renderer_factory(self, content_type: str):
        type(
            "Renderer",
            (Renderer,),
            {"content_type": content_type, "__call__": self.renderer_caller},
        )

    def test_negotiation_fails_if_no_renderer(self):
        with pytest.raises(NotAcceptable):
            Negotiator()
