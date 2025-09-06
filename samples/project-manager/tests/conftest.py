from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from cauldron_incubator import development
from cauldron_incubator.db import database as database
from cauldron_incubator.db.database import Database, Migrations
from cauldron_incubator.db.settings import PostgresqlSettings
from sqlalchemy.pool import NullPool

if TYPE_CHECKING:
    from collections.abc import Generator

    from alembic.config import Config
    from cauldron_incubator.application import Application
    from fastapi import FastAPI
    from project_manager.app import Configuration
    from sqlalchemy.engine import Engine

pytest.register_assert_rewrite("tests.api.scenario")


@pytest.fixture(scope="module")
def postgresql() -> Generator[None, Any]:
    # override the sqlalchemy poolclass as the queuepool works
    # badly in tests
    database.ASYNC_ENGINE_KWARGS["poolclass"] = NullPool
    with development.DevelopmentEnvironment().testcontainer_postgresql():
        yield


@pytest.fixture
def migrations():
    from project_manager.app import migrations  # noqa: PLC0415

    return migrations


@pytest.fixture
def db(
    postgresql: None, migrations: Migrations[PostgresqlSettings]
) -> Generator[None, Any]:
    migrations.upgrade()
    yield
    migrations.downgrade("base")


@pytest.fixture
def project_manager(
    postgresql: None, db: Database[PostgresqlSettings]
) -> Application[Configuration]:
    from project_manager.app import application  # noqa: PLC0415

    return application


@pytest.fixture
def app(project_manager: Application[Configuration]) -> FastAPI:
    return project_manager.app


@pytest.fixture
def alembic_config(postgresql: None, migrations: Migrations) -> Config:
    from project_manager.app import migrations  # noqa: PLC0415

    return migrations.migration_config()


@pytest.fixture
def alembic_engine(postgresql: None) -> Engine:
    return Database[PostgresqlSettings]().sync_engine
