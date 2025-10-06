from typing import Annotated
from brewing.http import BrewingHTTP, ViewSet
from brewing.http.testing import TestClient
from fastapi import Header
from pydantic import BaseModel


def app_with_viewsets(*viewsets: ViewSet) -> BrewingHTTP:
    """Provide asgi app instance for tests."""
    app = BrewingHTTP()
    for viewset in viewsets:
        app.include_viewset(viewset)
    return app


def new_client(*viewsets: ViewSet):
    """Provide a testclient for given viewsets."""
    return TestClient(app=app_with_viewsets(*viewsets))


class SomeData(BaseModel):
    """Basic response data structure."""

    something: list[int]
    data: str | None


def dependency(data: Annotated[str | None, Header()] = None):
    """Test dependency that parses from an HTTP header."""
    return data
