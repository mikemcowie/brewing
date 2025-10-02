"""
Viewset - the basic building block for http handlers in brewing.

The viewset is a wrapper/facade around fastapi's APIRouter, with
the structure and terminology influenced by Django's views
and Django Rest Framework's viewsets.
"""

from __future__ import annotations

from fastapi import APIRouter


class ViewSet:
    """A collection of related http endpoint handlers."""

    def __init__(self, router: APIRouter | None = None):
        self._router = router or APIRouter()
        # All the HTTP method decorators from the router
        # are made directly available so it can be used with
        # exactly the same decorator syntax in a functional manner.
        self.get = self.router.get
        self.post = self.router.post
        self.head = self.router.head
        self.put = self.router.put
        self.patch = self.router.patch
        self.delete = self.router.delete
        self.options = self.router.options
        self.trace = self.router.trace

    @property
    def router(self):
        """The underlying fastapi router."""
        return self._router
