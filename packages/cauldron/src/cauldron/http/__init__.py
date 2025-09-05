from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter as APIRouter
from fastapi import Depends as Depends
from fastapi import FastAPI
from fastapi import Path as Path
from fastapi import Request as Request
from fastapi import status as status

from .responses import Response as Response

if TYPE_CHECKING:
    from .viewset import AbstractViewSet

__all__ = ["APIRouter", "CauldronHTTP", "Request", "Response", "status"]


class CauldronHTTP(FastAPI):
    def include_viewset(self, viewset: AbstractViewSet):
        for attr in dir(viewset):
            # This allows us to refer to a method as a depdendency
            # during class definition time.
            item = getattr(viewset, attr)
            func = getattr(item, "__func__", None)
            if callable(item) and func:
                self.dependency_overrides[func] = item
        self.include_router(viewset.router)
