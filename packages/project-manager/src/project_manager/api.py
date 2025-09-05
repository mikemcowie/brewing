from __future__ import annotations

from functools import partial

from cauldron.application import Application
from cauldron.resources.router import model_crud_router

from project_manager.organizations.models import Organization

app_extra_args = {
    "title": "Project Manager Service",
    "description": "Maintains Filesystem Projects over time",
    "version": "0.0.1",
}
routers = (model_crud_router(Organization),)


def make_api(dev: bool):
    return Application(dev=dev, app_extra_args=app_extra_args, routers=routers).app


dev_api = partial(make_api, True)
api = partial(make_api, False)
