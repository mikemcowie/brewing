import pytest
import pytest_asyncio
from testing_samples import db_sample1

from brewing.db import Database, settings, testing


@pytest.fixture(scope="session", params=settings.DatabaseType)
def db_type(request: pytest.FixtureRequest):
    db_type: settings.DatabaseType = request.param
    return db_type


@pytest.fixture(scope="session")
def running_db_session(db_type: settings.DatabaseType):
    with testing.testing(db_type):
        yield


@pytest.fixture
def running_db(running_db_session: None, db_type: settings.DatabaseType):
    with testing.testing(db_type):
        yield


@pytest_asyncio.fixture
async def database_sample_1(running_db: None):
    db = Database(
        metadata=db_sample1.Base.metadata,
    )
    yield db
    await db.engine.dispose()
