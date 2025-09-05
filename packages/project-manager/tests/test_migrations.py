# ruff: noqa:F403
import pytest
from alembic.config import Config
from cauldron.db.database import Database
from cauldron.db.settings import PostgresqlSettings

# The actual test cases are imported from this file.
from pytest_alembic.tests.default import *  # type: ignore
from sqlalchemy.engine import Engine


@pytest.fixture
def alembic_config(postgresql: None) -> Config:
    return Database[PostgresqlSettings]().migration_config()


@pytest.fixture
def alembic_engine(postgresql: None) -> Engine:
    return Database[PostgresqlSettings]().sync_engine
