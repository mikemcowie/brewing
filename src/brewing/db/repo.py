"""Generic Repository implementation for brewing."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import DeclarativeBase

from brewing.db import db_session
from brewing.generic import runtime_generic


class NotFound(RuntimeError):
    """Item was not found in the database."""


class InvalidUpdate(RuntimeError):
    """Invalid update request."""


@runtime_generic
class Repository[ModelT: DeclarativeBase, PKType: Any]:
    model: type[ModelT]
    pk_type: type[PKType]

    def query(self) -> Select[tuple[ModelT]]:
        q = select(self.model)
        return q

    async def execute(self, query: Select[tuple[ModelT]]):
        async with db_session() as session:
            return (await session.execute(query)).scalars().all()

    async def create(self, item: ModelT) -> ModelT:
        """Add item to the repository."""
        async with db_session() as session:
            session.add(item)
            await session.flush()
        return item

    async def get(self, lookup: PKType, /) -> ModelT:
        """Retrieve an item by its primary_key."""
        async with db_session() as session:
            if item := await session.get(self.model, lookup):
                return item
            raise NotFound(f"{self.model.__name__} with {lookup=} was not found.")

    async def update(self, lookup: PKType, **update: Any) -> ModelT | None:
        """Retrieve an item by its primary_key."""
        async with db_session() as session:
            item = await session.get(self.model, lookup)
            error: Exception | None = None
            for k, v in update.items():
                if hasattr(item, k):
                    setattr(item, k, v)
                else:
                    error = InvalidUpdate(
                        f"object of type {type(item)} does not hae attibute {k}"
                    )
        if error:
            raise (error)

    async def delete(self, lookup: PKType, /) -> None:
        """Delete an item. Raises NotFound if it doesn't exist."""
        async with db_session() as session:
            if item := await self.get(lookup):
                await session.delete(item)
                await session.flush()
