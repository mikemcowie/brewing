import pytest
from cauldron_incubator.configuration import BaseConfiguration
from cauldron_incubator.old_cli import build_cli


def test_config_cannot_be_instantiated_with_unimplemented_attributes():
    with pytest.raises(TypeError) as err:
        BaseConfiguration()
    assert (
        "required class attributes missing: ['cli_provider', 'description', 'title', 'version']"
        in err.exconly()
    )


def test_config_instantiated_when_attributes_are_provided():
    class Configuration(BaseConfiguration):
        description = "Some test"
        title = "My System"
        version = "0.0.1"
        cli_provider = build_cli

    assert isinstance(Configuration(), Configuration)
