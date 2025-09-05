from __future__ import annotations

from cauldron.application import Application

app_extra_args = {
    "title": "Project Manager Service",
    "description": "Maintains Filesystem Projects over time",
    "version": "0.0.1",
}
api = Application(dev=False, app_extra_args=app_extra_args).app
dev_api = Application(dev=True, app_extra_args=app_extra_args).app
