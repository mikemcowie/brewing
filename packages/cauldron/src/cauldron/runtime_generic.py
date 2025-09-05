"""Provides a decorator that makes a given generic class able to be instantiated with generic syntax."""

from collections.abc import Callable
from functools import cache
from typing import TYPE_CHECKING, get_type_hints


def subclass_attributes(cls: type, types: tuple[type, ...]):
    annotations = get_type_hints(cls)
    unbound_class_attributes = set(annotations.keys()).difference(cls.__dict__.keys())
    if len(unbound_class_attributes) != len(types):
        raise TypeError(
            f"expected {len(unbound_class_attributes)} parameter(s), got {len(types)} parameter(s)."
        )
    return {
        k: dict(zip(cls.__parameters__, types, strict=True))[v.__parameters__[0]]
        for k, v in annotations.items()
    }


def concrete_subclasser[T](cls: type[T]) -> Callable[[type | tuple[type, ...]], type]:
    """Returns callable that modifies a class with a new __class_getitem__ method.

    This callable automatically returns a generated subclass
    with the specified class attribute filled in.
    """

    def subclass(generic_type: type | tuple[type, ...]):
        if not isinstance(generic_type, tuple):
            generic_type = (generic_type,)
        return type(
            f"{cls.__name__}[{','.join(t.__name__ for t in generic_type)}]",
            (cls,),
            subclass_attributes(cls, types=generic_type),
        )

    return subclass


def runtime_generic[T](cls: type[T]) -> type[T]:
    """Decorator that makes some class's generic be able to be instantiated."""
    subclasser = concrete_subclasser(cls)
    current_class_getitem = getattr(cls, "__class_getitem__", None)
    if current_class_getitem and current_class_getitem.__name__ == subclasser.__name__:
        raise RuntimeError(
            "Cannot decorate a class with runtime_generic more than once."
        )
    if not TYPE_CHECKING:
        # The type checkers get all sorts of upset about this call
        # But it works.
        cls.__class_getitem__ = cache(subclasser)

    return cls
