from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from cauldron.http import Request


async def db_session(request: Request) -> AsyncGenerator[AsyncSession, Any]:
    from cauldron.application import Application  # noqa: PLC0415

    assert isinstance(request.app.project_manager, Application)
    async with request.app.project_manager.database.session() as session:
        yield session
