from __future__ import annotations

import uuid

from brewing_incubator import (
    Application,
    BaseConfiguration,
    ModelViewSet,
    Resource,
    build_cli,
)
from brewing_incubator.db.database import Migrations
from sqlalchemy.orm import Mapped, mapped_column

UUID = uuid.UUID


class Organization(Resource, kw_only=True):
    plural_name = "organizations"
    singular_name = "organization"
    summary_fields = (*list(Resource.summary_fields), "name")
    id: Mapped[UUID] = Resource.primary_foreign_key_to(init=False)
    name: Mapped[str] = mapped_column(index=True)


class Configuration(BaseConfiguration):
    title = "Project Manager Service"
    description = "Maintains Filesystem Projects over time"
    version = "0.0.1"
    cli_provider = build_cli


vs = ModelViewSet[Organization]()
application = Application[Configuration](viewsets=[ModelViewSet[Organization]()])
migrations = Migrations(application.database, __file__)


def dev_api():
    return application.dev_app


def api():
    return application.app


cli = build_cli(api, dev_api, migrations)
