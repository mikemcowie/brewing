import pytest

from project_manager import testing
from project_manager.api import api_factory


@pytest.fixture(scope="session")
def postgresql():
    with testing.testcontainer_postgresql():
        yield


@pytest.fixture
def app():
    return api_factory()
