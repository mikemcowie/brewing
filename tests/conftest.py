import pytest

from project_manager import testing


@pytest.fixture(scope="session")
def postgresql():
    with testing.testcontainer_postgresql():
        yield
