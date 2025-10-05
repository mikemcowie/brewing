"""Unit tests for the viewset class."""

from typing import Annotated
from http import HTTPMethod
from brewing.http import ViewSet, BrewingHTTP, status
from brewing.http.endpoint_decorator import EndpointDecorator
from brewing.http.testing import TestClient
from fastapi import APIRouter, Header, Depends, Query, Request, HTTPException, Response
import pytest
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


@pytest.mark.parametrize("method", HTTPMethod)
def test_method_for_each_http_method_mapped_to_router(method: HTTPMethod):
    """Validate consistent structure of the decorators."""
    if method is HTTPMethod.CONNECT:
        pytest.skip("not supported")
        return
    fastapi_compat_decorator = getattr(vs1, method.value.lower())
    brewing_native_decorator = getattr(vs1, method.value.upper())
    assert fastapi_compat_decorator == getattr(vs1.router, method.value.lower())
    assert isinstance(brewing_native_decorator, EndpointDecorator)
    assert brewing_native_decorator.wraps == fastapi_compat_decorator


class SomeData(BaseModel):
    """Basic response data structure."""

    something: list[int]
    data: str | None


def dependency(data: Annotated[str | None, Header()] = None):
    """Test dependency that parses from an HTTP header."""
    return data


@vs1.get("/", response_model=SomeData)
def endpoint1(
    data: Annotated[str | None, Depends(dependency)], count: Annotated[int, Query()] = 0
):
    """Return some data."""
    return SomeData(something=[n for n in range(count)], data=data)


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


"""Functional viewset usage - still similar pattern to fastapi.

The upper-case method names in the decorators are used for the brewing-specific variants.
"""
vs2 = ViewSet()


@vs2.GET("/", response_model=SomeData)
def vs2_new_decorator_with_fastapi_style(
    data: Annotated[str | None, Depends(dependency)], count: Annotated[int, Query()] = 0
):
    """Fastapi style  ."""
    return SomeData(something=[n for n in range(count)], data=data)


def test_new_decorator_with_fastapi_style_endpoint():
    """Test that the above declared fastapi style endpoint works as per fastapi."""
    client = new_client(vs2)
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["something"] == []
    response = client.get("/?count=2")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["something"] == [0, 1]
    response = client.get("/", headers={"data": "foo"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"] == "foo"


vs3 = ViewSet()


@vs3.GET
def vs3_new_decorator_simplified_decorator(
    data: Annotated[str | None, Depends(dependency)], count: Annotated[int, Query()] = 0
):
    """The method itself is a valid decorator, corresping to the root of the viewset."""
    return SomeData(something=[n for n in range(count)], data=data)


def test_new_decorator_simplified_usage():
    """Test that the above declared fastapi style endpoint works as per fastapi."""
    client = new_client(vs3)
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["something"] == []
    response = client.get("/?count=2")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["something"] == [0, 1]
    response = client.get("/", headers={"data": "foo"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"] == "foo"


vs4 = ViewSet()
items = vs4("items")
item_id = items("{item_id}")


@items.GET
def vs4_with_new_path_style(
    data: Annotated[str | None, Depends(dependency)], count: Annotated[int, Query()] = 0
):
    """The method itself is a valid decorator, corresping to the root of the viewset."""
    return SomeData(something=[n for n in range(count)], data=data)


def test_new_decorator_new_pathing():
    """Test that the above declared fastapi style endpoint works as per fastapi."""
    client = new_client(vs4)
    response = client.get("/items/")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["something"] == []
    response = client.get("/items/?count=2")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["something"] == [0, 1]
    response = client.get("/items/", headers={"data": "foo"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"] == "foo"


@item_id.GET
def vs4_with_path_param(item_id: int) -> dict[str, str | int]:
    """Return an item of type int."""
    return {"type": "item", "id": item_id}


def test_new_decorator_new_pathing_with_var():
    """Test that the above declared fastapi style endpoint works as per fastapi."""
    client = new_client(vs4)
    response = client.get("/items/1")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json() == {"type": "item", "id": 1}


"""In addition to standard HTTP methods, a  DEPENDS can be declared which functions as a prerequisite for all HTTP methods, and all nested endpoints."""

vs5 = ViewSet()
items = vs5("items")
item_id = items("{item_id}")


@items.DEPENDS
def must_provide_header(request: Request):
    if value := request.headers.get("required-header"):
        return value
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="nope, can't do that."
    )


@items.GET
def get_items() -> list[SomeData]:
    return []


@items.POST
def create_item(data: SomeData) -> SomeData:
    return data


@item_id.GET
def get_item_by_id(
    item_id: int, value: Annotated[str, Depends(must_provide_header)]
) -> SomeData:
    return SomeData(something=[item_id], data=value)


@items.DEPENDS
def extra_dependency(response: Response):
    """A dependency declared after the routes, to make sure that a dependency can be declared after endpoints too."""
    response.headers["extra-header"] = "yes"


def test_depends_blocking_path():
    # Dependency blocks requests that don't get through the dependency
    client = new_client(vs5)
    response = client.get("/items/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "nope, can't do that."}
    response = client.post(
        "/items/", json=SomeData(something=[], data="").model_dump(mode="json")
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "nope, can't do that."}
    response = client.get("/items/1")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "nope, can't do that."}


def test_depends_passing_path():
    """If header is set, these endpoints give 200."""
    client = new_client(vs5)
    client.headers["required-header"] = "somevalue"
    response = client.get("/items/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
    assert response.headers["extra-header"] == "yes"
    response = client.post(
        "/items/", json=SomeData(something=[], data="").model_dump(mode="json")
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"something": [], "data": ""}
    assert response.headers["extra-header"] == "yes"
    response = client.get("/items/1")
    # And the fastapi-style dependency in this endpoint works too.
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"something": [1], "data": "somevalue"}
    assert response.headers["extra-header"] == "yes"
