import pytest
from sqlalchemy.pool import NullPool

import project_manager.db
from project_manager import testing
from project_manager.api import api_factory
from project_manager.db import Database


@pytest.fixture(scope="session")
def postgresql():
    # override the sqlalchemy poolclass as the queuepool works
    # badly in tests
    project_manager.db.ASYNC_ENGINE_KWARGS["poolclass"] = NullPool
    with testing.testcontainer_postgresql():
        yield


@pytest.fixture
def db(postgresql: None):
    db_ = Database()
    db_.upgrade()
    yield
    db_.downgrade()


@pytest.fixture
def app(db: Database):
    return api_factory()
