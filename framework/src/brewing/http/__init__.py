"""An http toolkit built on fastapi."""

from brewing.http.viewset import ViewSet as ViewSet
from brewing.http.asgi import BrewingHTTP as BrewingHTTP
from fastapi import status as status


self = object()  ## TODO - move it!

__all__ = ["ViewSet", "BrewingHTTP", "status"]
