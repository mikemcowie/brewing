"""Configurations: the data holders used to configure brewing and its components."""

from __future__ import annotations

import importlib
import os
from contextlib import contextmanager
from typing import Annotated, Any, get_type_hints

from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer

from brewing.context import env


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


class BaseOptions(BaseModel):
    """Base model from which all configurations inherit.

    It holds information about the class it is a configuration for.
    """

    # extra: allow allows the base class to initially be usued
    # even when it's going to switch to a sub class subsequently.
    model_config = ConfigDict(extra="allow")


class EnvDTO[OptionsT: BaseOptions](BaseModel):
    """Object to be transported via environment variable as JSON value."""

    cls: Annotated[
        type[EnvPushable],
        PlainSerializer(type_to_string),
        BeforeValidator(string_to_type),
    ]
    options_cls: Annotated[
        type[OptionsT], PlainSerializer(type_to_string), BeforeValidator(string_to_type)
    ]
    options: OptionsT


class EnvPushableMeta(type):
    """Metaclass where __instancecheck__  performs the following checks:

    * object has an "options" value that us an instance of BaseConfig
    """

    def __instancecheck__(cls, instance: Any) -> bool:
        return all(
            (
                hasattr(instance, "options"),
                isinstance(instance.options, BaseOptions),
                hasattr(instance, "__init__"),
                list(get_type_hints(instance.__init__).keys()) == ["options"],
                issubclass(
                    next(iter(get_type_hints(instance.__init__).values())), BaseOptions
                ),
            )
        )


class EnvPushable[OptionsT: BaseOptions](metaclass=EnvPushableMeta):
    """Base class for objects that can be pushed and pulled through environment variables to subprocesses."""

    def __init__(self, options: OptionsT) -> None:
        self.options = options


@contextmanager
def push_to_env(obj: EnvPushable[Any], env_var: str):
    with env(
        {
            env_var: EnvDTO(
                cls=obj.__class__,
                options=obj.options,
                options_cls=obj.options.__class__,
            ).model_dump_json()
        }
    ):
        yield


def pull_from_env[T: EnvPushable[Any]](env_var: str, check_type: type[T]) -> T:
    dto: EnvDTO[Any] = EnvDTO.model_validate_json(os.environ[env_var])
    retval = dto.cls(options=dto.options_cls(**dto.options.model_dump()))
    if not isinstance(retval, check_type):
        raise TypeError(f"{retval} is not instance of {check_type}")
    return retval
