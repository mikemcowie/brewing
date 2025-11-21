"""An http toolkit built on fastapi."""

from fastapi import Cookie as Cookie
from fastapi import Depends as Depends
from fastapi import Header as Header
from fastapi import Path as Path
from fastapi import Query as Query
from fastapi import Response as Response
from fastapi import Security as Security
from fastapi import status as status
from fastapi.responses import HTMLResponse as HTMLResponse
from fastapi.responses import JSONResponse as JSONResponse
from fastapi.responses import PlainTextResponse as PlainTextResponse
from fastapi.responses import StreamingResponse as StreamingResponse

from brewing.http.asgi import BrewingHTTP as BrewingHTTP
from brewing.http.path import self
from brewing.http.viewset import ViewSet as ViewSet
from brewing.http.viewset import ViewsetOptions as ViewsetOptions

__all__ = [
    "BrewingHTTP",
    "Cookie",
    "Depends",
    "HTMLResponse",
    "Header",
    "JSONResponse",
    "Path",
    "PlainTextResponse",
    "Query",
    "Response",
    "Security",
    "StreamingResponse",
    "ViewSet",
    "ViewsetOptions",
    "self",
    "status",
]
