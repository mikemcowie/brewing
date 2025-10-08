"""Functional viewset usage - the path component is removed"""

from typing import Annotated
from brewing.http import ViewSet, status
from .helpers import SomeData, new_client, dependency
from fastapi import Depends, Query


vs2 = ViewSet()


@vs2.GET(response_model=SomeData, status_code=status.HTTP_200_OK, operation_id="SomeOp")
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


def test_decorator_args_applied_correctly():
    """Validate that arbitart extra arg in the decorator applies as expected."""
    openapi_response = new_client(vs2).get("/openapi.json")
    assert openapi_response.status_code == status.HTTP_200_OK
    # we specified a custom operation_id in the decorator. Check it was read.
    assert openapi_response.json()["paths"]["/"]["get"]["operationId"] == "SomeOp"


vs3 = ViewSet()


@vs3.GET()
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


@items.GET()
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


@item_id.GET()
def vs4_with_path_param(item_id: int) -> dict[str, str | int]:
    """Return an item of type int."""
    return {"type": "item", "id": item_id}


def test_new_decorator_new_pathing_with_var():
    """Test that the above declared fastapi style endpoint works as per fastapi."""
    client = new_client(vs4)
    response = client.get("/items/1")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json() == {"type": "item", "id": 1}
