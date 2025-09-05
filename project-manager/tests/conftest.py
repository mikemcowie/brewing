from collections.abc import Generator
from typing import Any

import pytest
from cauldron import db as db_
from cauldron.db import Database
from fastapi import FastAPI
from sqlalchemy.pool import NullPool

from project_manager import testing
from project_manager.application import Application

pytest.register_assert_rewrite("tests.api.scenario")


@pytest.fixture(scope="session")
def postgresql() -> Generator[None, Any]:
    # override the sqlalchemy poolclass as the queuepool works
    # badly in tests
    db_.ASYNC_ENGINE_KWARGS["poolclass"] = NullPool
    with testing.testcontainer_postgresql():
        yield


@pytest.fixture
def db(postgresql: None) -> Generator[None, Any]:
    db_ = Database()
    db_.upgrade()
    yield
    db_.downgrade("base")


@pytest.fixture
def project_manager(postgresql: None, db: Database) -> Application:
    return Application(dev=True)


@pytest.fixture
def app(project_manager: Application) -> FastAPI:
    return project_manager.app
