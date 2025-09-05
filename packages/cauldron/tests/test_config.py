import pytest
from cauldron.config import BaseConfiguration


def test_config_cannot_be_instantiated_with_unimplemented_attributes():
    with pytest.raises(TypeError) as err:
        BaseConfiguration()
    assert (
        "required class attributes missing: ['description', 'title', 'version']"
        in err.exconly()
    )


def test_config_instantiated_when_attributes_are_provided():
    class Configuration(BaseConfiguration):
        description = "Some test"
        title = "My System"
        version = "0.0.1"

    assert isinstance(Configuration(), Configuration)
