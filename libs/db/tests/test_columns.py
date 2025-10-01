import time
from typing import Any

import pytest
import pytest_asyncio
import sqlalchemy as sa
from brewinglib.db import Database, columns, mixins, new_base, settings, testing, types
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

Base = new_base()


class SomeThing(mixins.AuditMixin, mixins.UUIDPrimaryKey, Base, kw_only=True):
    json_col: Mapped[dict[str, Any]] = mapped_column(columns.json_column_type)


class HasIncrementingPrimaryKey(
    mixins.AuditMixin, mixins.IncrementingIntPK, Base, kw_only=True
):
    pass


def test_server_generated_uuid_pk():
    column = columns.uuid_primary_key(sa.func.some())
    assert not column.column.default
    assert column.column.server_default


@pytest_asyncio.fixture
async def db(db_type: settings.DatabaseType, running_db_session: None):
    return Database[db_type.dialect().connection_config_type](Base.metadata)


@pytest.mark.asyncio
async def test_incrementing_pk[ConfigT: types.DatabaseConnectionConfiguration](
    db: Database[ConfigT],
):
    async with testing.upgraded(db):
        instances = [HasIncrementingPrimaryKey() for _ in range(20)]
        assert {instance.id for instance in instances} == {None}
        async with db.session() as session:
            session.add_all(instances)
            await session.commit()
        async with db.session() as session:
            read_instances = (
                (await session.execute(sa.select(HasIncrementingPrimaryKey)))
                .scalars()
                .all()
            )
        assert {instance.id for instance in read_instances} == set(range(1, 21))


@pytest.mark.asyncio
async def test_uuid_pk[ConfigT: types.DatabaseConnectionConfiguration](
    db: Database[ConfigT],
):
    async with testing.upgraded(db):
        instances = [SomeThing(json_col={"item": n}) for n in range(20)]
        async with db.session() as session:
            session.add_all(instances)
            await session.commit()
        async with db.session() as session:
            read_instances = (
                (await session.execute(sa.select(SomeThing))).scalars().all()
            )
        assert sorted([str(item.json_col) for item in read_instances]) == sorted(
            [str({"item": n}) for n in range(20)]
        )


@pytest.mark.asyncio
async def test_created_updated_field_match_after_create[
    ConfigT: types.DatabaseConnectionConfiguration
](db: Database[ConfigT]):
    async with testing.upgraded(db):
        instance = SomeThing(json_col={"item": 1})
        async with db.session() as session:
            session.add(instance)
            await session.commit()
        async with db.session() as session:
            read_instance = (
                (await session.execute(sa.select(SomeThing))).scalars().one()
            )
            assert read_instance.created_at
            assert read_instance.updated_at
            assert (
                0
                <= read_instance.updated_at.timestamp()
                - read_instance.created_at.timestamp()
                < 1
            )


@pytest.mark.asyncio
async def test_created_updated_field_changed_after_record_updated[
    ConfigT: types.DatabaseConnectionConfiguration
](db: Database[ConfigT]):
    async with testing.upgraded(db):
        instance = SomeThing(json_col={"item": 1})
        async with db.session() as session:
            session.add(instance)
            await session.commit()
        time.sleep(1.01)
        async with db.session() as session:
            read_instance = (
                (await session.execute(sa.select(SomeThing))).scalars().one()
            )
            assert read_instance.created_at
            assert read_instance.updated_at
            orig_created = read_instance.created_at
            orig_updated = read_instance.updated_at
            query = (
                sa.update(SomeThing)
                .where(SomeThing.id == read_instance.id)
                .values({"json_col": {"different": "value"}})
            )
            await session.execute(query)
            await session.commit()

        async with db.session() as session:
            read_instance = (
                (await session.execute(sa.select(SomeThing))).scalars().one()
            )
            assert read_instance.created_at
            assert read_instance.updated_at
            assert (
                read_instance.created_at.timestamp()
                < read_instance.updated_at.timestamp()
            )
            new_created = read_instance.created_at
            new_updated = read_instance.updated_at
            assert orig_created == new_created
            assert orig_updated < new_updated
