"""Content negotiation.

In the context of brewing this is analgous to "selecting the renderer from a list".
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Protocol

from content_negotiation import NoAgreeableContentTypeError, decide_content_type

from brewing.http import HTTPException, status
from brewing.http.serialization.base import Renderer

if TYPE_CHECKING:
    from collections.abc import Iterable

    from brewing.http.serialization.base import Renderer


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
        self, accepts: Iterable[str], renderers: Iterable[Renderer[Any, Any]]
    ) -> Renderer[Any, Any]: ...


class TrivialNegotiator(Negotiator):
    """A negotiator that always returns the first renderer."""

    def select(
        self,
        accepts: Iterable[str],  # noqa: ARG002
        renderers: Iterable[Renderer[Any, Any]],
    ) -> Renderer[Any, Any]:
        try:
            return next(iter(renderers))
        except StopIteration as error:
            raise NotAcceptable(detail="No valid renderers available.") from error


class ContentNegotiation(Negotiator):
    """Content negotiation via the content-negotiation library."""

    def select(
        self, accepts: Iterable[str], renderers: Iterable[Renderer[Any, Any]]
    ) -> Renderer[Any, Any]:
        server_supports = {r.content_type: r for r in renderers}
        try:
            return server_supports[
                decide_content_type(
                    accept_headers=list(accepts),
                    supported_content_types=list(server_supports.keys()),
                )
            ]
        except NoAgreeableContentTypeError as error:
            raise NotAcceptable(
                detail={
                    "message": "Content negotiation error",
                    "client_accepts": list(accepts),
                    "server_supports": list(server_supports.keys()),
                }
            ) from error
