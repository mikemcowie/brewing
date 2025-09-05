from collections.abc import Sequence
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

from cauldron.http import CauldronHTTP, Depends
from cauldron.http.viewset import (
    AbstractViewSet,
    APIPathConstant,
    EndpointParameters,
    HTTPMethod,
    collection,
)
from cauldron.testing import TestClient
from pydantic import BaseModel


class ConcreteViewSet(AbstractViewSet):
    def get_router_dependencies(self) -> Sequence[Any]:
        return []

    def get_router_tags(self) -> list[str | Enum]:
        return ["test"]

    def get_base_path(self) -> Sequence[str]:
        return [APIPathConstant("test")]


def test_routes_created():
    """Given a class with a couple of method endpoints,
    routes should get attached.
    """

    class ViewSet(ConcreteViewSet):
        @collection.GET(status_code=200)
        def list_things(self):
            pass

    expected_params = EndpointParameters(
        path=Path("/"),
        trailing_slash=True,
        method=HTTPMethod.GET,
        args=(),
        kwargs={"status_code": 200},
    )
    assert ViewSet.list_things.__dict__["_cauldron_endpoint_params"] == expected_params
    vs = ViewSet()
    assert vs.list_things.__dict__["_cauldron_endpoint_params"] == expected_params
    assert vs.router.routes


def test_http_response():
    class Thing(BaseModel):
        name: str
        is_large: bool

    class ViewSet(ConcreteViewSet):
        @collection.GET(status_code=200, response_model=list[Thing])
        def list_things(self, large: bool = False):
            return [Thing(name="thing1", is_large=large)]

    vs = ViewSet()
    app = CauldronHTTP()
    app.include_viewset(vs)
    client = TestClient(app)
    result = client.get("/test/")
    assert result.status_code == 200
    assert result.json() == [{"name": "thing1", "is_large": False}]


def test_collection_path():
    class ViewSet(ConcreteViewSet):
        def get_base_path(self) -> Sequence[str]:
            return ["api", "v1", "thing"]

        @collection.GET(status_code=200)
        async def endpoint(self):
            return "happy"

    app = CauldronHTTP()
    app.include_viewset(ViewSet())
    client = TestClient(app)
    result = client.get("/test/")
    assert result.status_code == 404
    result = client.get("/api/v1/thing/")
    assert result.status_code == 200
    assert result.content == b'"happy"'


def test_depends():
    class ViewSet(ConcreteViewSet):
        async def message(self):
            return "something"

        @collection.GET(status_code=200)
        async def give_message(self, message: Annotated[str, Depends(message)]):
            return message

    app = CauldronHTTP()
    app.include_viewset(ViewSet())
    client = TestClient(app)
    result = client.get("/test/")
    assert result.status_code == 200, result.content
    assert result.content == b'"something"'


def test_depends_manager_independtly_across_viewsets():
    """The first version of the dependency manager operates

    Could get messy with several similar viewsets sharing a dependency
    through overrides

    Here we test the behaviour.
    """

    class Base(ConcreteViewSet):
        _message = "base"

        async def message(self):
            return self._message

        @collection.GET(status_code=200)
        async def give_message(self, message: Annotated[str, Depends(message)]):
            return message

    class VS1(Base):
        _message = "vs1"

        def get_base_path(self) -> Sequence[str]:
            return ["path1"]

        async def message(self):
            return self._message

        @collection.GET(status_code=200)
        async def give_message(self, message: Annotated[str, Depends(message)]):
            return message

    class VS2(Base):
        _message = "vs2"

        def get_base_path(self) -> Sequence[str]:
            return ["path2"]

        async def message(self):
            return self._message

        @collection.GET(status_code=200)
        async def give_message(self, message: Annotated[str, Depends(message)]):
            return message

    vs1 = VS1()
    vs2 = VS2()

    app = CauldronHTTP()
    app.include_viewset(vs1, vs2)
    client = TestClient(app)
    result = client.get("/path1/")
    assert result.status_code == 200, result.content
    assert result.content == b'"vs1"'
    result = client.get("/path2/")
    assert result.status_code == 200, result.content
    assert result.content == b'"vs2"'


def test_path_parameter():
    class ViewSet(ConcreteViewSet):
        per_message_id = collection.path_parameter("message_id")

        @per_message_id.GET()
        async def give_message(self, message_id: int):
            return message_id

    app = CauldronHTTP()
    app.include_viewset(ViewSet())
    client = TestClient(app)
    result = client.get("/test/5")
    assert result.status_code == 200
    assert result.content == b"5"


def test_action_on_collection():
    class Payload(BaseModel):
        foo: str
        data: dict[str, str]

    class InvokeResponse(BaseModel):
        message: str

    class ViewSet(ConcreteViewSet):
        invoke_action = collection.action("invoke")

        @invoke_action.POST(status_code=201, response_model=InvokeResponse)
        async def invoke(self, data: Payload):
            return InvokeResponse(
                message=f"successfully invoked with {data.model_dump_json()}"
            )

    app = CauldronHTTP()
    app.include_viewset(ViewSet())
    client = TestClient(app)
    result = client.post("/test/invoke", json={"foo": "bar", "data": {}})
    assert result.status_code == 201
    assert result.json() == {
        "message": 'successfully invoked with {"foo":"bar","data":{}}'
    }
