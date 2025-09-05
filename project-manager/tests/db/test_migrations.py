# ruff: noqa:F403
import pytest
from alembic.config import Config

# The actual test cases are imported from this file.
from pytest_alembic.tests.default import *  # type: ignore
from sqlalchemy.engine import Engine

from cauldron.db import Database


@pytest.fixture
def alembic_config(postgresql: None) -> Config:
    return Database().migration_config()


@pytest.fixture
def alembic_engine(postgresql: None) -> Engine:
    return Database().sync_engine
