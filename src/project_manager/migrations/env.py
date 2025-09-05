from alembic import context


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # late import to avoid circular import

    from project_manager.db import Database  # noqa: PLC0415

    db = Database()
    with db.sync_engine.connect() as connection:
        context.configure(connection=connection, target_metadata=db.metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise NotADirectoryError()
else:
    run_migrations_online()
