import pytest
from brewinglib.db import Database, settings, testing


@pytest.fixture(scope="session", params=settings.DatabaseType)
def db_type(request: pytest.FixtureRequest):
    db_type: settings.DatabaseType = request.param
    return db_type


@pytest.fixture(scope="session")
def running_db(db_type: settings.DatabaseType):
    with testing.testing(db_type):
        yield


@pytest.fixture
def database(db_type: settings.DatabaseType, running_db: None):
    return Database[db_type.dialect().connection_config_type]()
