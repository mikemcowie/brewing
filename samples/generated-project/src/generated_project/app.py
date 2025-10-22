from pathlib import Path

from brewing import Brewing, Settings
from brewing.db import Database, new_base
from brewing.db.settings import PostgresqlSettings
from brewing.healthcheck.viewset import HealthCheckViewset
from brewing.http import BrewingHTTP

# register database models by inheriting from this base.
# brewing will automatically scan for modules inheriting from this
# while starting up, to ensure consistent database metadadta.
Base = new_base()

# construct the application by providing the settings and components that make up the app.
with Settings(
    database=Database[PostgresqlSettings](
        metadata=Base.metadata,
        revisions_directory=Path(__file__).parent / "db_revisions",
    )
):
    app = Brewing(
        "generated-project", http=BrewingHTTP().with_viewsets(HealthCheckViewset())
    )


def __getattr__(name: str):
    return getattr(app, name)
