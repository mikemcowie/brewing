from __future__ import annotations

import os
from typing import (
    TYPE_CHECKING,
    Any,
)

from starlette import responses

if TYPE_CHECKING:
    from collections.abc import Mapping

    from starlette.background import BackgroundTask
    from starlette.datastructures import URL
    from starlette.types import Receive, Scope, Send


class BrewingResponse[InternalT: Any, WrapsT: responses.Response](responses.Response):
    """Brewing's wrapper around starlette Response classes.

    It inherits from and offers the same API as a starlette response,
    just with additional static generic type parameters.
    """

    wraps: type[WrapsT]
    internal_t: type[InternalT]

    def __init__(
        self,
        content: InternalT = None,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        self._wrapped = self.wraps(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type or self.wraps.media_type,
            background=background,
        )

    def __getattr__(self, name: Any):
        return getattr(self._wrapped, name)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        return await self._wrapped(scope, receive, send)


class PlainTextResponse(BrewingResponse[str, responses.PlainTextResponse]):
    wraps = responses.PlainTextResponse


type JSONCompatible = (
    dict[str, float | str | None | list[JSONCompatible]] | list[JSONCompatible]
)


class JSONResponse(BrewingResponse[JSONCompatible, responses.JSONResponse]):
    wraps = responses.JSONResponse


class HTMLResponse(BrewingResponse[str, responses.HTMLResponse]):
    wraps = responses.HTMLResponse


class RedirectResponse(BrewingResponse[str, responses.RedirectResponse]):
    wraps = responses.RedirectResponse

    def __init__(
        self,
        url: str | URL,
        status_code: int = 307,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
    ):
        self._wrapped = self.wraps(
            url=url,
            status_code=status_code,
            headers=headers,
            background=background,
        )


class StreamingResponse[InternalT: Any](
    BrewingResponse[InternalT, responses.StreamingResponse]
):
    wraps = responses.StreamingResponse


class FileResponse(BrewingResponse[os.PathLike[str], responses.FileResponse]):
    wraps = responses.FileResponse

    def __init__(  # noqa: PLR0913
        self,
        path: str | os.PathLike[str],
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
        filename: str | None = None,
        stat_result: os.stat_result | None = None,
        method: str | None = None,
        content_disposition_type: str = "attachment",
    ):
        self._wrapped = self.wraps(
            path=path,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
            filename=filename,
            stat_result=stat_result,
            method=method,
            content_disposition_type=content_disposition_type,
        )
