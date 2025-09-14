import pytest
from brewinglib.db import testing, types


@pytest.fixture(scope="session", params=types.DatabaseType)
def db_type(request: pytest.FixtureRequest):
    db_type: types.DatabaseType = request.param
    return db_type


@pytest.fixture(scope="session")
def running_db(db_type: types.DatabaseType):
    with testing.testing(db_type):
        yield
