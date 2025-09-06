from unittest.mock import MagicMock

from brewing_incubator.application import Application
from brewing_incubator.configuration import BaseConfiguration
from starlette.routing import Mount


def new_config_cls():
    class Config(BaseConfiguration):
        cli_provider = MagicMock()
        title = "Test"
        description = "Test Config"
        version = "1"

    return Config


def test_dev_api_extra_mounts():
    config = new_config_cls()
    app = Application[config](viewsets=[])
    dev_mount_paths = [p.path for p in app.dev_app.routes if isinstance(p, Mount)]
    prod_mount_paths = [p.path for p in app.app.routes if isinstance(p, Mount)]
    assert not prod_mount_paths
    assert dev_mount_paths == ["/htmlcov", "/testreport"]
