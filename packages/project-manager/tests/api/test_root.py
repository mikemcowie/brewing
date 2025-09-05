from fastapi import FastAPI, status
from fastapi.testclient import TestClient


def test_root_endpoint(app: FastAPI) -> None:
    client = TestClient(app)
    result = client.get("/")
    assert result.status_code == status.HTTP_200_OK
    assert result.json()["title"] == "Project Manager"
