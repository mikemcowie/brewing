from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from cauldron import db as db_
from cauldron import development
from cauldron.application import Application
from cauldron.db import Database
from sqlalchemy.pool import NullPool

if TYPE_CHECKING:
    from collections.abc import Generator

    from fastapi import FastAPI
    from project_manager.app import Configuration

pytest.register_assert_rewrite("tests.api.scenario")


@pytest.fixture(scope="module")
def postgresql() -> Generator[None, Any]:
    # override the sqlalchemy poolclass as the queuepool works
    # badly in tests
    db_.ASYNC_ENGINE_KWARGS["poolclass"] = NullPool
    with development.DevelopmentEnvironment().testcontainer_postgresql():
        yield


@pytest.fixture
def db(postgresql: None) -> Generator[None, Any]:
    db_ = Database()
    db_.upgrade()
    yield
    db_.downgrade("base")


@pytest.fixture
def project_manager(postgresql: None, db: Database) -> Application[Configuration]:
    from project_manager.app import Configuration, routers  # noqa: PLC0415

    return Application[Configuration](routers=routers)


@pytest.fixture
def app(project_manager: Application[Configuration]) -> FastAPI:
    return project_manager.app
