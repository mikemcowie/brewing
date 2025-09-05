# ruff: noqa:F403
import pytest
from alembic.config import Config
from cauldron.db import Database
from cauldron.settings import Settings

# The actual test cases are imported from this file.
from pytest_alembic.tests.default import *  # type: ignore
from sqlalchemy.engine import Engine


@pytest.fixture
def alembic_config(postgresql: None) -> Config:
    return Database[Settings]().migration_config()


@pytest.fixture
def alembic_engine(postgresql: None) -> Engine:
    return Database[Settings]().sync_engine
