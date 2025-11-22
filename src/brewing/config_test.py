"""Configurations: the data holders used to configure brewing and its components."""

from __future__ import annotations

from brewing import config as c


class Target:
    pass


def test_type_serializer():
    """Test we can declare a field with type type[T] 4

    It should be able to be serialized/deserialized through JSON."""
    initial = c.BaseConfig(cls=Target)
    json = initial.model_dump_json()
    final = c.BaseConfig.model_validate_json(json)
    assert final.cls is Target
    assert initial == final


def test_type_serializer_transmitted_by_environment():
    """Affirm we can use environment variables to transmit the object"""
    initial = c.BaseConfig(cls=Target)
    with c.push_to_env(initial):
        final = pull_from_env(Target)
    assert final.cls is Target
    assert initial == final
