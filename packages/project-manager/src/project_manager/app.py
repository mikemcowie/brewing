from __future__ import annotations

import uuid
from functools import partial

from cauldron.application import make_api
from cauldron.cli import build_cli
from cauldron.resources.models import Resource
from cauldron.resources.router import model_crud_router
from sqlalchemy.orm import Mapped, mapped_column

UUID = uuid.UUID


class Organization(Resource, kw_only=True):
    plural_name = "organizations"
    singular_name = "organization"
    summary_fields = (*list(Resource.summary_fields), "name")
    id: Mapped[UUID] = Resource.primary_foreign_key_to(init=False)
    name: Mapped[str] = mapped_column(index=True)


app_extra_args = {
    "title": "Project Manager Service",
    "description": "Maintains Filesystem Projects over time",
    "version": "0.0.1",
}
routers = (model_crud_router(Organization),)


dev_api = partial(make_api, True)
api = partial(make_api, False)
cli = build_cli("project_manager.app:api", "project_manager.app:dev_api")
