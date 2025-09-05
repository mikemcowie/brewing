"""Provides a decorator that makes a given generic class able to be instantiated with generic syntax."""

from functools import cache
from typing import TYPE_CHECKING, TypeVar, get_type_hints


class _GenericClassProcessor:
    def __init__(self, cls: type):
        self.cls = cls

    @property
    def annotations(self):
        return get_type_hints(self.cls)

    @property
    def unbound_class_attributes(self):
        return set(self.annotations.keys()).difference(self.__class__.__dict__.keys())

    @property
    def parameters(self) -> tuple[TypeVar]:
        return self.cls.__parameters__

    def subclass_attributes(self, types: tuple[type, ...]):
        attributes = tuple(attr for attr in self.unbound_class_attributes)
        if len(attributes) != len(types):
            raise TypeError(
                f"expected {len(attributes)} parameter(s), got {len(types)} parameter(s)."
            )
        target_attributes_unrendered: dict[str, tuple[TypeVar]] = {
            k: v.__parameters__ for k, v in self.annotations.items()
        }
        param_to_type = dict(zip(self.parameters, types, strict=True))
        for key, value in target_attributes_unrendered.items():
            if len(value) != 1:
                raise TypeError(
                    f"Cannot generate subclass of {self.cls}; class attribute {key} is generic on {len(value)} parameters, but must be generic on exactly 1 parameter."
                )

        # if len(attributes) > 2:
        #   raise Exception(param_to_type)
        #   raise Exception("Err\n" + "\n".join([str(target_attributes_unrendered), str(types), str(self.parameters)]))

        return dict(
            zip(
                attributes,
                (
                    param_to_type[attr.__parameters__[0]]
                    for attr in self.annotations.values()
                ),
                strict=True,
            )
        )

    def concrete_subclasser(self):
        """Returns callable that modifies a class with a new __class_getitem__ method.

        This callable automatically returns a generated subclass
        with the specified class attribute filled in.
        """

        def subclass(generic_type: type | tuple[type, ...]):
            if not isinstance(generic_type, tuple):
                generic_type = (generic_type,)
            return type(
                f"{self.cls.__name__}[{','.join(t.__name__ for t in generic_type)}]",
                (self.cls,),
                self.subclass_attributes(types=generic_type),
            )

        return subclass

    def enhance(self):
        subclass = self.concrete_subclasser()
        current_class_getitem = getattr(self.cls, "__class_getitem__", None)
        if (
            current_class_getitem
            and current_class_getitem.__name__ == subclass.__name__
        ):
            raise RuntimeError(
                "Cannot decorate a class with runtime_generic more than once."
            )
        if not TYPE_CHECKING:
            # The type checkers get all sorts of upset about this call
            # But it works.
            self.cls.__class_getitem__ = cache(subclass)

        return self.cls


def runtime_generic[T](cls: type[T]) -> type[T]:
    """Decorator that makes some class's generic be able to be instantiated."""
    return _GenericClassProcessor(cls).enhance()
