"""Provides a decorator that makes a given generic class able to be instantiated with generic syntax."""

from functools import cache
from typing import get_type_hints


def runtime_generic[T](cls: type[T]) -> type[T]:
    """Decorator that makes some class's generic be able to be instantiated.

    Given a class of type T, decorating with this will allow creation of a subclass
    with generic parameters mapped to matching unbound class attributes.

    # Example
    ```python
    @runtime_generic
    class SomeGenericClass[A, B]:
        attr_a: type[A]
        attr_b: type[B]


    class ThingA:
        thinga = "foo"


    class ThingB:
        thingb = "bar"


    assert SomeGenericClass[ThingA, ThingB].thinga == "foo"
    assert SomeGenericClass[ThingA, ThingB].thingb == "bar"
    ```
    """

    def subclass(types: type | tuple[type, ...]):
        """Function applied to class as __class_getitem__  in order to enable runtime generic."""
        nonlocal cls
        annotations = get_type_hints(cls)
        unbound_class_attributes = set(annotations.keys()).difference(
            cls.__dict__.keys()
        )
        if not isinstance(types, tuple):
            types = (types,)
        if len(unbound_class_attributes) != len(types):
            raise TypeError(
                f"expected {len(unbound_class_attributes)} parameter(s), got {len(types)} parameter(s)."
            )
        if not isinstance(types, tuple):
            types = (types,)
        return type(
            f"{cls.__name__}[{','.join(t.__name__ for t in types)}]",
            (cls,),
            {
                k: dict(zip(cls.__parameters__, types, strict=True))[
                    v.__parameters__[0]
                ]
                for k, v in annotations.items()
            },
        )

    cls.__class_getitem__ = cache(subclass)  # type: ignore
    return cls
