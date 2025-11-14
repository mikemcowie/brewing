"""Tests for the healthcheck package."""

import pytest
from typing import Generator
from brewing.healthcheck.viewset import HealthCheckViewset, HealthCheckOptions
from brewing.http.testing import TestClient
from brewing.http import BrewingHTTP, status
from brewing.db import testing as testing_db
from brewing.db import Database, MetaData
from brewing.db.settings import SQLiteSettings, DatabaseType
from brewing.db.types import DatabaseProtocol
from brewing.app import BrewingOptions


@pytest.fixture
def database() -> Generator[DatabaseProtocol, None, None]:
    """Return a database"""
    with testing_db.testing(DatabaseType.sqlite):
        yield Database[SQLiteSettings](metadata=MetaData())


@pytest.fixture
def client(database: DatabaseProtocol) -> Generator[TestClient, None, None]:
    """Return a testclient that can test the viewset."""
    with BrewingOptions(name="test", database=database):
        app = BrewingHTTP()
        app.with_viewsets(HealthCheckViewset(HealthCheckOptions()))
        client = TestClient(app=app)
        with client:
            yield client


def test_alivez(client: TestClient):
    result = client.get("/livez")
    assert result.status_code == status.HTTP_200_OK


def test_readyz(client: TestClient):
    result = client.get("/readyz")
    assert result.status_code == status.HTTP_200_OK


def test_readyz_fail_when_database_down(
    client: TestClient, database: DatabaseProtocol, capsys: pytest.CaptureFixture[str]
):
    def fail(*_, **__):
        raise RuntimeError("The database failed somehow.")

    database.is_alive = fail
    result = client.get("/readyz")
    assert result.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    out, err = capsys.readouterr()
    assert "The database failed somehow" in err + out
    assert "RuntimeError" in err + out
