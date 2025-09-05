from __future__ import annotations

from project_manager import constants
from project_manager.project_manager import ProjectManager

app_extra_args = {
    "title": constants.TITLE,
    "description": constants.DESCRIPION,
    "version": constants.API_VERSION,
}
api = ProjectManager(dev=False, app_extra_args=app_extra_args).app
dev_api = ProjectManager(dev=True, app_extra_args=app_extra_args).app
