"""The brewingHTTP class: the ASGI application.

A subclass of FastAPI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI

from .responses import Response as Response

if TYPE_CHECKING:
    from .viewset import AbstractViewSet


logger = structlog.get_logger()


class BrewingHTTP(FastAPI):
    def include_viewset(self, *args: AbstractViewSet):
        for viewset in args:
            self.include_router(viewset.router)
