from fastapi import status
from fastapi.testclient import TestClient

from project_manager.api import api_factory


def test_root_endpoint():
    api = api_factory(title="Foo")
    client = TestClient(api)
    result = client.get("/")
    assert result.status_code == status.HTTP_200_OK
    assert result.json()["title"] == "Foo"
