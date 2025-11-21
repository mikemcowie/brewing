"""Generic Repository implementation for brewing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from testing_samples.db_sample1 import Base, Item

from brewing.db import Database, settings, testing
from brewing.db.repo import InvalidUpdate, NotFound, Repository

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from pytest_subtests import SubTests


ItemRepo = Repository[Item]


@pytest_asyncio.fixture
async def repo() -> AsyncGenerator[ItemRepo]:
    with testing.testing(settings.DatabaseType.sqlite):
        database = Database[settings.SQLiteSettings](Base.metadata)
        async with database.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        with database():
            yield ItemRepo()
        await database.engine.dispose()
        async with database.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_crud_operations_repo(repo: ItemRepo, subtests: SubTests):
    # Given a repo with db context setup
    # And checking that the repo  returns no items
    with subtests.test("given empty repo"):
        assert (await repo.execute(repo.query())) == []
    item = Item(description="some-item", price=4.0)
    assert not item.item_id
    with subtests.test("create"):
        assert await repo.create(item)
        # Expect a primary key was assigned
        assert item.item_id
        # And the item can now be retrieved
        assert (await repo.execute(repo.query())) == [item]
    with subtests.test("read"):
        assert (await repo.get(item.item_id)) == item
    with subtests.test("update"):
        await repo.update(item.item_id, description="Changed Value")
        item = await repo.get(item.item_id)
        assert item.description == "Changed Value"
    with subtests.test("invalid-update"), pytest.raises(InvalidUpdate):
        await repo.update(item.item_id, invalid_key="Changed Value")
    with subtests.test("delete"):
        await repo.delete(item.item_id)
        with pytest.raises(NotFound):
            assert await repo.delete(item.item_id) is False
        assert (await repo.execute(repo.query())) == []
