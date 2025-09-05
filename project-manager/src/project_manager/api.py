from __future__ import annotations

from cauldron.application import Application
from project_manager import constants

app_extra_args = {
    "title": constants.TITLE,
    "description": constants.DESCRIPION,
    "version": constants.API_VERSION,
}
api = Application(dev=False, app_extra_args=app_extra_args).app
dev_api = Application(dev=True, app_extra_args=app_extra_args).app
