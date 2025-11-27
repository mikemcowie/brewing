# ruff: noqa: PLC0415
from pathlib import Path

from brewing import Brewing
from brewing.db import Database, new_base
from brewing.db.settings import PostgresqlSettings
from brewing.http import BrewingHTTP

# register database models by inheriting from this base.
# brewing will automatically scan for modules inheriting from this
# while starting up, to ensure consistent database metadadta.
Base = new_base()


def app():
    """Application loading callable."""
    # You are likely to need to delay imports until inside this function
    # To avoid circular imports of models inheriting from Base .
    from brewing.healthcheck.viewset import HealthCheckViewset

    return Brewing(
        name="generated-project",
        database=Database(
            metadata=Base.metadata,
            revisions_directory=Path(__file__).parent / "db_revisions",
            config_type=PostgresqlSettings,
        ),
        components={"http": BrewingHTTP(viewsets=[HealthCheckViewset()])},
    )
