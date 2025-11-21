from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import MetaData, text
from testing_samples import db_sample1

from brewing.db import (
    Database,
    NoCurrentDatabaseContextSet,
    database,
    get_session,
    testing,
)

if TYPE_CHECKING:
    from pytest_subtests import SubTests

    from brewing.db.settings import DatabaseType
    from brewing.db.types import DatabaseProtocol


@pytest.mark.asyncio
async def test_engine_cached(db_type: DatabaseType, running_db: None):
    dialect = db_type.dialect()
    db = Database[dialect.connection_config_type](MetaData())
    assert db.engine is db.engine
    assert db.engine.url.drivername == f"{db_type.value}+{dialect.dialect_name}"


@pytest.mark.asyncio
async def test_connect_with_engine(database_sample_1: DatabaseProtocol):
    async with database_sample_1.engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
    assert len(list(result)) == 1


def test_default_migrations_revisions_directory(
    db_type: DatabaseType, running_db: None
):
    dialect = db_type.dialect()
    db = Database[dialect.connection_config_type](MetaData())
    assert (
        db.migrations.revisions_dir == (Path(__file__).parent / "revisions").resolve()
    )


@pytest.mark.asyncio
async def test_sample1(database_sample_1: DatabaseProtocol):
    async with testing.upgraded(database_sample_1):
        await db_sample1.run_sample(database_sample_1)


@pytest.mark.asyncio
async def test_error_raised_when_calling_global_session_without_context():
    assert database.current is None
    with pytest.raises(NoCurrentDatabaseContextSet):
        async with get_session():
            pass


@pytest.mark.asyncio
async def test_global_session(
    database_sample_1: DatabaseProtocol,
    subtests: SubTests,
):
    with subtests.test("global-session-matches-scoped-session"):
        assert database.current is None
        with database_sample_1():
            assert database.current
            async with (
                database_sample_1.current_session() as from_db_session,
                get_session() as global_session,
            ):
                assert from_db_session is global_session

        assert database.current is None
    with (
        subtests.test("global-session-maintained-in-nested-context"),
        database_sample_1(),
    ):
        async with get_session() as session1:
            async with get_session() as session2:
                assert session1 is session2
    with (
        subtests.test("global-session-changed-in-subsequent-context"),
        database_sample_1(),
    ):
        async with get_session() as session1:
            pass
        async with get_session() as session2:
            pass
        assert session1 is not session2


@pytest.mark.asyncio
async def test_global_session_threading(
    database_sample_1: DatabaseProtocol,
    subtests: SubTests,
):
    async def _provide_session():
        async with get_session() as session:
            return session

    with subtests.test("threading"), database_sample_1():
        # Session objects are not threadsafe
        # and hence when executing another thread
        # our contextmanager should return another session.
        async with get_session() as session_from_main_thread:
            with ThreadPoolExecutor() as exectuor:
                future = exectuor.submit(lambda: asyncio.run(_provide_session()))
            session_from_threadpool = future.result()
        assert session_from_threadpool is not session_from_main_thread

    with subtests.test("aio"), database_sample_1():
        async with get_session() as session_from_parent_task:
            # Sessions are safe to run concurrently via aio
            session_from_same_task = await _provide_session()
            session_from_child_task = await asyncio.create_task(_provide_session())
        assert session_from_parent_task is session_from_same_task
        assert session_from_parent_task is session_from_child_task
