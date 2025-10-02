"""Unit tests for the viewset class."""

from typing import Annotated
from . import ViewSet, BrewingHTTP, status
from .testing import TestClient
from fastapi import APIRouter, Header, Depends, Query
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


def test_viewset_router_if_not_provided():
    """A router is created if it was not provided."""
    assert isinstance(ViewSet().router, APIRouter)


def test_viewset_router_if_provided():
    """If a router was provided, it is used."""
    router = APIRouter()
    assert ViewSet(router=router).router is router


"""Viewset can be used as a proxy for fastapi APIRouter."""
vs1 = ViewSet()


class ReturningData(BaseModel):
    """Basic response data structure."""

    something: list[int]
    data: str | None


def dependency(data: Annotated[str | None, Header()] = None):
    """Test dependency that parses from an HTTP header."""
    return data


@vs1.get("/", response_model=ReturningData)
def endpoint1(
    data: Annotated[str | None, Depends(dependency)], count: Annotated[int, Query()] = 0
):
    """Return some data."""
    return ReturningData(something=[n for n in range(count)], data=data)


def test_functional_fastapi_style_endpoint():
    """Test that the above declared fastapi style endpoint works as per fastapi."""
    client = new_client(vs1)
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["something"] == []
    response = client.get("/?count=2")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["something"] == [0, 1]
    response = client.get("/", headers={"data": "foo"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"] == "foo"
