"""Generic Repository implementation for brewing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from testing_samples.sample1 import Item

from brewing.db import Database, db_session, settings, testing
from brewing.db.repo import InvalidUpdate, NotFound, Repository

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from pytest_subtests import SubTests


ItemRepo = Repository[Item, int]


@pytest_asyncio.fixture
async def repo(db_sample_1: Database) -> AsyncGenerator[ItemRepo]:
    with testing.testing(settings.DatabaseType.sqlite):
        async with testing.upgraded(db_sample_1):
            yield ItemRepo()


@pytest.mark.asyncio
async def test_crud_operations_repo(repo: ItemRepo, subtests: SubTests):
    # Given a repo with db context setup
    # And checking that the repo  returns no items
    with subtests.test("given empty repo"):
        assert (await repo.execute(repo.query())) == []
    item = Item(description="some-item", price=4.0)
    assert not item.item_id
    async with db_session():
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
