"""Configurations: the data holders used to configure brewing and its components."""

from __future__ import annotations

import importlib
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer


def type_to_string(cls: type[Any]) -> str:
    return f"{cls.__module__}:{cls.__qualname__}"


def string_to_type(value: type[Any] | str) -> type[Any]:
    if isinstance(value, type):
        return value
    module_name, cls_name = value.split(":")
    module = importlib.import_module(module_name)
    cls = getattr(module, cls_name)
    if not isinstance(cls, type):
        raise TypeError(f"{cls=} must be a type.")
    return cls


class BaseConfig(BaseModel):
    """Base model from which all configurations inherit.

    It holds information about the class it is a configuration for.
    """

    model_config = ConfigDict(
        # We can deserialize objects that were origonally subclasses to BaseConfig
        # and they will work fine in a duck-type manner.
        extra="allow"
    )
    cls: Annotated[
        type[Any], PlainSerializer(type_to_string), BeforeValidator(string_to_type)
    ]


class Target:
    pass


def test_type_serializer():
    """Test we can declare a field with type type[T] 4

    It should be able to be serialized/deserialized through JSON."""
    initial = BaseConfig(cls=Target)
    json = initial.model_dump_json()
    final = BaseConfig.model_validate_json(json)
    assert final.cls is Target
    assert initial == final
