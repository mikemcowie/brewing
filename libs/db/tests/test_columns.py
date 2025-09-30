import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
import pytest_asyncio
import sqlalchemy as sa
from brewinglib.db import Database, settings, testing, types
from pydantic.alias_generators import to_snake
from sqlalchemy.dialects import mysql, sqlite
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    declared_attr,
    mapped_column,
)

json_column_type = (
    sa.JSON()
    .with_variant(pg.JSONB, "postgresql")
    .with_variant(sqlite.JSON, "sqlite")
    .with_variant(mysql.JSON, "mysql", "mariadb")
)
uuid_column_type = (
    sa.UUID().with_variant(pg.UUID, "postgresql").with_variant(sa.String(36), "mysql")
)
type NewUUIDFactory = Callable[[], uuid.UUID] | sa.Function[Any]


# on python 3.14, client-generateduuid7 will be the default
# older versions, client-generated uuid4 will be default
try:
    uuid_default_provider = uuid.uuid7  # type: ignore
except AttributeError:
    uuid_default_provider = uuid.uuid4


def uuid_primary_key(uuid_provider: NewUUIDFactory = uuid_default_provider):
    """A UUID"""
    if isinstance(uuid_provider, sa.Function):
        return mapped_column(
            uuid_column_type, primary_key=True, server_default=uuid_provider, init=False
        )  # type: ignore
    else:
        return mapped_column(
            uuid_column_type,
            primary_key=True,
            default_factory=uuid_provider,
            init=False,
        )


def created_at_column(**kwargs: Any):
    """A column that stores the datetime that the record was created."""
    return mapped_column(
        sa.DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        init=False,
        **kwargs,
    )


def updated_at_column():
    """A column that stores the datetime that the record was last updated."""
    return created_at_column(onupdate=lambda: datetime.now(UTC))


class AuditMixin(MappedAsDataclass):
    @declared_attr
    def created_at(self) -> Mapped[datetime]:
        return created_at_column()

    @declared_attr
    def updated_at(self) -> Mapped[datetime]:
        return updated_at_column()


def new_base():
    """Returns a new base class with a new metadata."""

    class OurBase(MappedAsDataclass, DeclarativeBase, kw_only=True):
        metadata = sa.MetaData()

        @declared_attr  # type: ignore
        def __tablename__(cls) -> str:  # noqa: N805
            return to_snake(cls.__name__)

    return OurBase


BaseForAllDialects = new_base()


class UUIDBase(BaseForAllDialects, kw_only=True):
    __abstract__ = True
    id: Mapped[uuid.UUID] = uuid_primary_key()


class IncrementingInt(AuditMixin, BaseForAllDialects):
    __abstract__ = True
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)


class SomeThing(AuditMixin, UUIDBase, kw_only=True):
    json_col: Mapped[dict[str, Any]] = mapped_column(json_column_type)


class HasIncrementingPrimaryKey(IncrementingInt, kw_only=True):
    pass


@pytest_asyncio.fixture
async def db(db_type: settings.DatabaseType, running_db_session: None):
    return Database[db_type.dialect().connection_config_type](
        BaseForAllDialects.metadata
    )


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
