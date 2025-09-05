"""Provides a decorator that makes a given generic class able to be instantiated with generic syntax."""

from collections.abc import Callable
from functools import cache
from typing import TYPE_CHECKING


def runtime_generic[T_OUTER](
    attribute: str,
) -> Callable[[type[T_OUTER]], type[T_OUTER]]:
    """Decorator that makes some class's generic be able to be instantiated."""

    def enhance[T_INNER: type](cls: T_INNER) -> T_INNER:
        def concrete_subclass_factory[TypeT, GenericT](
            cls: type[TypeT], generic_type: type[GenericT]
        ):
            """Modifies class to have a __class_getitem__ method.

            This method automatically returns a generated subclass
            with the specified class attribute filled in.
            """
            return type(
                f"{cls.__name__}[{generic_type.__name__}]",
                (cls,),
                {attribute: generic_type},
            )

        current_class_getitem = getattr(cls, "__class_getitem__", None)
        if (
            current_class_getitem
            and current_class_getitem.__name__ == concrete_subclass_factory.__name__
        ):
            raise RuntimeError(
                "Cannot decorate a class with runtime_generic more than once."
            )
        if not TYPE_CHECKING:
            # The type checkers get all sorts of upset about this call
            # But it works.
            cls.__class_getitem__ = classmethod(cache(concrete_subclass_factory))

        return cls

    return enhance
