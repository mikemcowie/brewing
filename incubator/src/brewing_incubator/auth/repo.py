from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from brewing_incubator.auth.models import User, UserSession


class UserRepo:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def flush(self):
        await self._session.flush()

    async def commit(self):
        await self._session.commit()

    async def validated(self, token_digest: str) -> UserSession | None:
        return (
            await self._session.execute(
                select(UserSession)
                .where(UserSession.id == token_digest)
                .where(UserSession.expires > datetime.now(UTC))
            )
        ).scalar_one_or_none()

    async def user_from_email(self, username: str) -> User | None:
        return (
            await self._session.execute(select(User).where(User.email == username))
        ).scalar_one_or_none()

    async def add(self, item: UserSession | User, flush: bool = False):
        self._session.add(item)
        if flush:
            await self.flush()
