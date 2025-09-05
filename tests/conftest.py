import pytest

from project_manager import testing
from project_manager.api import api_factory
from project_manager.db import Database


@pytest.fixture(scope="session")
def postgresql():
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
