"""Testing utilities for brewing.http."""

from brewing.http import BrewingHTTP, ViewSet
from typing import Any
from fastapi.testclient import TestClient as TestClient


__all__ = ["TestClient", "app_with_viewsets", "new_client"]


def app_with_viewsets(*viewsets: ViewSet[Any]) -> BrewingHTTP:
    """Provide asgi app instance for tests."""
    app = BrewingHTTP()
    for viewset in viewsets:
        app.include_viewset(viewset)
    return app


def new_client(*viewsets: ViewSet[Any]):
    """Provide a testclient for given viewsets."""
    return TestClient(app=app_with_viewsets(*viewsets))
