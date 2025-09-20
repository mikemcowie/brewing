import pytest
import pytest_asyncio
from brewinglib.db import Database, settings, testing
from sqlalchemy import MetaData
from testing_samples import db_sample1


@pytest.fixture(scope="session", params=settings.DatabaseType)
def db_type(request: pytest.FixtureRequest):
    db_type: settings.DatabaseType = request.param
    return db_type


@pytest.fixture(scope="session")
def running_db_session(db_type: settings.DatabaseType):
    with testing.testing(db_type):
        yield


@pytest_asyncio.fixture()
async def refresh_engine(db_type: settings.DatabaseType, running_db_session: None):
    engine = Database[db_type.dialect().connection_config_type](MetaData()).engine
    # "Disposing" the engine here helps avoid the dreaded "attached to a different event loop"
    # As, within the migrations machinery, we do dip in and out of new event loops, and we
    # can't maintain a common connection pool through this.
    await engine.dispose()


@pytest.fixture
def running_db(running_db_session: None, refresh_engine: None):
    return


@pytest.fixture
def database_sample_1(db_type: settings.DatabaseType, running_db: None):
    return Database[db_type.dialect().connection_config_type](db_sample1.Base.metadata)
