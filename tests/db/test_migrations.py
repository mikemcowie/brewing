# ruff: noqa:F403
import pytest

# The actual test cases are imported from this file.
from pytest_alembic.tests.default import *  # type: ignore

from project_manager.db import Database


@pytest.fixture
def alembic_config(postgresql):
    return Database().migration_config()


@pytest.fixture
def alembic_engine(postgresql):
    return Database().sync_engine
