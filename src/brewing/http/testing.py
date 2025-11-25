"""Testing utilities for brewing.http."""

from fastapi.testclient import TestClient as TestClient

from brewing.http import BrewingHTTP, ViewSet

__all__ = ["TestClient", "new_client"]


def new_client(*viewsets: ViewSet):
    """Provide a testclient for given viewsets."""
    return TestClient(app=BrewingHTTP(viewsets))
