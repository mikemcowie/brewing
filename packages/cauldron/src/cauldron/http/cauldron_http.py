"""The CauldronHTTP class: the ASGI application.

A subclass of FastAPI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI

from .responses import Response as Response

if TYPE_CHECKING:
    from .viewset import AbstractViewSet


class CauldronHTTP(FastAPI):
    def include_viewset(self, *args: AbstractViewSet):
        for viewset in args:
            for attr in dir(viewset):
                # This allows us to refer to a method as a depdendency
                # during class definition time.
                item = getattr(viewset, attr)
                func = getattr(item, "__func__", None)
                if callable(item) and func:
                    self.dependency_overrides[func] = item
            self.include_router(viewset.router)
