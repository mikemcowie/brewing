import pytest
import pytest_asyncio
from brewinglib.db import Database, settings, testing
from testing_samples import db_sample1


@pytest.fixture(scope="session", params=settings.DatabaseType)
def db_type(request: pytest.FixtureRequest):
    db_type: settings.DatabaseType = request.param
    return db_type


@pytest.fixture(scope="session")
def running_db_session(db_type: settings.DatabaseType):
    with testing.testing(db_type):
        yield


@pytest.fixture
def running_db(db_type: settings.DatabaseType):
    with testing.testing(db_type):
        yield


@pytest_asyncio.fixture
async def database_sample_1(db_type: settings.DatabaseType, running_db: None):
    return Database[db_type.dialect().connection_config_type](db_sample1.Base.metadata)
