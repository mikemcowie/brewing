from collections.abc import AsyncGenerator
from typing import Any

from cauldron_incubator.http import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def db_session(request: Request) -> AsyncGenerator[AsyncSession, Any]:
    from cauldron.application import Application  # noqa: PLC0415

    assert isinstance(request.app.project_manager, Application)
    async with request.app.project_manager.database.session() as session:
        yield session
