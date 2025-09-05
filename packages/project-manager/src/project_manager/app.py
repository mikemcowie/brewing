from __future__ import annotations

import uuid
from functools import partial
from typing import TYPE_CHECKING

from cauldron.application import Application
from cauldron.cli import build_cli
from cauldron.config import BaseConfiguration
from cauldron.resources.models import Resource
from cauldron.resources.router import model_crud_router
from sqlalchemy.orm import Mapped, mapped_column

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastapi import APIRouter

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


routers = (model_crud_router(Organization),)


def make_api(dev: bool, routers: Sequence[APIRouter]):
    return Application[Configuration](dev=dev, routers=routers).app


dev_api = partial(make_api, True, routers)
api = partial(make_api, False, routers)
cli = build_cli("project_manager.app:api", "project_manager.app:dev_api")
