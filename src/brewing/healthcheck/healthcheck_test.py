"""Tests for the healthcheck package."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from brewing import Brewing
from brewing.db import Database, MetaData
from brewing.db import testing as testing_db
from brewing.db.settings import DatabaseType, SQLiteSettings
from brewing.healthcheck.viewset import HealthCheckViewset
from brewing.http import BrewingHTTP, status
from brewing.http.testing import TestClient

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def database() -> Generator[Database]:
    """Return a database"""
    with testing_db.testing(DatabaseType.sqlite):
        yield Database(metadata=MetaData(), config_type=SQLiteSettings)


@pytest.fixture
def client(database: Database) -> Generator[TestClient]:
    """Return a testclient that can test the viewset."""
    app = BrewingHTTP(viewsets=(HealthCheckViewset(),))
    brewing = Brewing(
        name="test",
        database=database,
        components={"app": app},
    )
    with brewing:
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
    client: TestClient, database: Database, capsys: pytest.CaptureFixture[str]
):
    def fail(*_, **__):
        raise RuntimeError("The database failed somehow.")

    database.is_alive = fail
    result = client.get("/readyz")
    assert result.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    out, err = capsys.readouterr()
    assert "The database failed somehow" in err + out
    assert "RuntimeError" in err + out
