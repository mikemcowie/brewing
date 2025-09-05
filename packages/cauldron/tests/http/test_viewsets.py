from collections.abc import Sequence
from enum import Enum
from typing import Any

from cauldron.http import CauldronHTTP
from cauldron.http.viewset import (
    AbstractViewSet,
    APIPathConstant,
    APIPathParam,
    collection,
)
from cauldron.testing import TestClient
from pydantic import BaseModel


class ConcreteViewSet(AbstractViewSet):
    def get_router_dependencies(self) -> Sequence[Any]:
        return []

    def get_router_tags(self) -> list[str | Enum]:
        return ["test"]

    def get_base_path(self) -> Sequence[APIPathConstant | APIPathParam]:
        return [APIPathConstant("test")]


def test_routes_created():
    """Given a class with a couple of method endpoints,
    routes should get attached.
    """

    class ViewSet(ConcreteViewSet):
        @collection.GET(status_code=200)
        def list_things(self):
            pass

    assert ViewSet.list_things.__dict__["_cauldron_endpoint_params"] == {
        "path": "/",
        "method": "GET",
        "args": (),
        "kwargs": {"status_code": 200},
    }
    vs = ViewSet()
    assert vs.list_things.__dict__["_cauldron_endpoint_params"] == {
        "path": "/",
        "method": "GET",
        "args": (),
        "kwargs": {"status_code": 200},
    }
    assert vs.router.routes


def test_http_response():
    class Thing(BaseModel):
        name: str
        is_large: bool

    class ViewSet(ConcreteViewSet):
        @collection.GET(status_code=200, response_model=list[Thing])
        def list_things(self, large: bool = False):
            return [Thing(name="thing1", is_large=large)]

    app = CauldronHTTP()
    app.include_router(ViewSet().router)
    client = TestClient(app)
    result = client.get("/")
    assert result.status_code == 200
    assert result.json() == [{"name": "thing1", "is_large": False}]
