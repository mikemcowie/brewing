from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import pytest
from brewing_incubator.auth.repo import UserRepo
from sqlalchemy import ForeignKey, MetaData, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    metadata = MetaData()


class User(MappedAsDataclass, Base, kw_only=True):
    __tablename__ = "user"

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)
    email: Mapped[str] = mapped_column()
    password: Mapped[str] = mapped_column()


class UserSession(MappedAsDataclass, Base, kw_only=True):
    __tablename__ = "user_session"
    metadata = MetaData()
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default_factory=uuid4,
    )
    user: Mapped[User] = relationship(lazy="joined")  # type: ignore
    user_id: Mapped[UUID] = mapped_column(ForeignKey(User.id), init=False)


async def new_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all)
    return engine


def new_session(engine: AsyncEngine):
    return AsyncSession(bind=engine)


@asynccontextmanager
async def repo(engine: AsyncEngine):
    async with new_session(engine) as session:
        yield UserRepo(session)


@pytest.mark.asyncio
async def test_user_add():
    engine = await new_engine()
    async with new_session(engine) as session:
        all_users = (await session.execute(select(User))).scalars().all()
        assert all_users == []
    async with repo(engine) as r:
        user1 = User(email="user1@example.com", password="FooDeeBarBar")
        user2 = User(email="user2@example.com", password="FooDeeBarBar")
        await r.add(user1, flush=True)  # type: ignore
        await r.add(user2)  # type: ignore
        emails = [user1.email, user2.email]
        await r.commit()

    async with new_session(engine) as session:
        all_users = (await session.execute(select(User))).scalars().all()
        assert len(all_users) == 2, all_users
        assert sorted([u.email for u in all_users]) == sorted(emails)
