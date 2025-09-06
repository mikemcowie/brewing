from alembic import context

from cauldron_incubator.db.database import Database
from cauldron_incubator.db.settings import PostgresqlSettings


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # late import to avoid circular import

    from cauldron_incubator.db.base import Base  # noqa: PLC0415

    with Database[PostgresqlSettings]().sync_engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():  # pragma: no cover
    raise NotImplementedError()
else:
    run_migrations_online()
