import pytest
import pytest_asyncio
from testing_samples import sample1

from brewing import Brewing
from brewing.db import Database, settings, testing


@pytest.fixture(scope="session", params=settings.DatabaseType)
def db_type(request: pytest.FixtureRequest):
    db_type: settings.DatabaseType = request.param
    return db_type


@pytest.fixture(scope="session")
def running_db_session(db_type: settings.DatabaseType):
    with testing.testing(db_type):
        yield


@pytest_asyncio.fixture
async def db_sample_1(db_type: settings.DatabaseType):
    db = Database(base=sample1.Base, db_type=db_type)
    app = Brewing(name="test", database=db, components={})
    with testing.testing(db_type), app:
        yield db
    await db.engine.dispose()


@pytest.fixture
def running_db(
    db_sample_1: Database, running_db_session: None, db_type: settings.DatabaseType
):
    with testing.testing(db_type):
        yield
