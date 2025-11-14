"""In addition to standard HTTP methods, a  DEPENDS can be declared which functions as a prerequisite for all HTTP methods, and all nested endpoints."""

from typing import Annotated
from brewing.http import ViewSet, ViewsetOptions, status
from .helpers import SomeData, new_client
from fastapi import Depends, Request, HTTPException, Response


vs1 = ViewSet(ViewsetOptions())
items = vs1("items")
item_id = items("{item_id}")


@items.DEPENDS()
def must_provide_header(request: Request):
    if value := request.headers.get("required-header"):
        return value
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="nope, can't do that."
    )


@items.GET()
def get_items() -> list[SomeData]:
    return []


@items.POST()
def create_item(data: SomeData) -> SomeData:
    return data


@item_id.GET()
def get_item_by_id(
    item_id: int, value: Annotated[str, Depends(must_provide_header)]
) -> SomeData:
    return SomeData(something=[item_id], data=value)


@items.DEPENDS()
def extra_dependency(response: Response):
    """A dependency declared after the routes, to make sure that a dependency can be declared after endpoints too."""
    response.headers["extra-header"] = "yes"


@item_id.DEPENDS()
def item_id_only_dep(response: Response):
    """Used to test that a dependency on an endpoint doesn't get applied to the parent endpoint."""
    response.headers["item-id-only-dep-handled-this"] = "yes"


def test_depends_blocking_path():
    # Dependency blocks requests that don't get through the dependency
    client = new_client(vs1)
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
    client = new_client(vs1)
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


def test_depends_not_applied_on_parent():
    """If depends is set on a child endpoint, it doesn't apply to parent endpoint."""
    # Given a dependency on the item_id endpoint
    # If we call the item_id endpoint
    client = new_client(vs1)
    client.headers["required-header"] = "somevalue"
    response = client.get("/items/1")
    assert response.status_code == status.HTTP_200_OK
    # then the response header will show the dependency was run.
    assert response.headers["item-id-only-dep-handled-this"] == "yes"
    # but if we call the parent items endpoint
    response = client.get("/items")
    assert response.status_code == status.HTTP_200_OK
    # then no such header will be present
    # showing that the dependency did not run.
    assert not response.headers.get("item-id-only-dep-handled-this")
