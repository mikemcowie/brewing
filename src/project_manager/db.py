from contextlib import asynccontextmanager, contextmanager
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData
from sqlalchemy.engine import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from project_manager import migrations
from project_manager.settings import Settings

MIGRATIONS_DIR = Path(migrations.__file__).parent.resolve()
VERSIONS_DIR = MIGRATIONS_DIR / "versions"


if TYPE_CHECKING:
    _engine = create_engine
    _async_engine = create_async_engine
else:

    @cache
    def _engine(*args, **kwargs):
        return create_engine(*args, **kwargs)

    @cache
    def _async_engine(*args, **kwargs):
        return create_engine(*args, **kwargs)


class Database:
    metadata = MetaData()

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.async_engine = _async_engine(url=self.build_uri("asyncpg"))
        self.sync_engine = _engine(url=self.build_uri("psycopg"))

    def build_uri(self, driver: str):
        return f"postgresql+{driver}://{self.settings.PGUSER}:{self.settings.PGPASSWORD.get_secret_value()}@{self.settings.PGHOST}:{self.settings.PGPORT}/{self.settings.PGDATABASE}"

    @contextmanager
    def session(self):
        with Session(bind=self.sync_engine) as sess:
            yield sess

    @asynccontextmanager
    async def async_session(self):
        async with AsyncSession(bind=self.async_engine) as sess:
            yield sess

    def migration_config(self):
        config = Config()
        config.set_main_option("script_location", "project_manager:migrations")
        return config

    def upgrade(self, revision: str = "head"):
        command.upgrade(self.migration_config(), revision=revision, sql=False)

    def downgrade(self, revision: str = "-1"):
        command.downgrade(self.migration_config(), revision=revision, sql=False)

    def stamp(self, revision: str = "head"):
        command.stamp(self.migration_config(), revision=revision)

    def create_revision(self, message: str, autogenerate: bool):
        command.revision(
            self.migration_config(),
            rev_id=f"{len(list(VERSIONS_DIR.glob('*.py'))):05d}",
            message=message,
            autogenerate=autogenerate,
        )
