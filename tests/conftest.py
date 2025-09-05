from collections.abc import Generator
from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy.pool import NullPool

import project_manager.db
from project_manager import testing
from project_manager.api import api_factory
from project_manager.db import Database


@pytest.fixture(scope="session")
def postgresql() -> Generator[None, Any]:
    # override the sqlalchemy poolclass as the queuepool works
    # badly in tests
    project_manager.db.ASYNC_ENGINE_KWARGS["poolclass"] = NullPool
    with testing.testcontainer_postgresql():
        yield


@pytest.fixture
def db(postgresql: None) -> Generator[None, Any]:
    db_ = Database()
    db_.upgrade()
    yield
    db_.downgrade()


@pytest.fixture
def app(db: Database) -> FastAPI:
    return api_factory()
