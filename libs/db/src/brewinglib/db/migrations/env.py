import asyncio

from alembic import context
from brewinglib.db.migrate import MigrationsConfig, current_config
from sqlalchemy.engine import Connection

target_metadata = None


def do_run_migrations(connection: Connection, config: MigrationsConfig) -> None:
    context.configure(connection=connection, target_metadata=config.metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    config = current_config()
    async with config.engine.connect() as connection:
        await connection.run_sync(do_run_migrations, config)

    await config.engine.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if current_config(default=None):
    if context.is_offline_mode():
        raise NotImplementedError("offline mirations not supported.")
    else:
        run_migrations_online()
