"""
1-line decorator to allow a class to be subclassed via generic syntax.

Specifically limited to the pattern where:

1. a class variable is declared, unbound, as type[T], where T is a generic class parameter.
2. An arbitary amount of such type parameters can be handled.

# Example

```python
from brewing.generic import runtime_generic


@runtime_generic
class SomeGenericClass[A, B]:
    attr_a: type[A]
    attr_b: type[B]


class ThingA:
    thinga = "foo"


class ThingB:
    thingb = "bar"


assert SomeGenericClass[ThingA, ThingB]().attr_a.thinga == "foo"
assert SomeGenericClass[ThingA, ThingB]().attr_b.thingb == "bar"
```

"""

from functools import cache
from typing import Any, TypeVar, get_type_hints


def _get_type_hints(cls: type):
    hints: dict[str, Any] = {}

    for item in reversed(cls.__mro__):
        hints = hints | get_type_hints(item)
    return hints


def _get_class_attributes(cls: type):
    attrs: set[str] = set()
    for item in cls.__mro__:
        for key in item.__dict__:
            attrs.add(key)
    return attrs


def runtime_generic[T](cls: type[T]) -> type[T]:
    """
    Make some class cls able to be subclassed via generic, i.e. Foo[Bar] syntax.

    Given a class Cls of type T, decorating with this will allow creation of a subclass
    Cls[T] with generic parameter T mapped to a matching unbound class attribute.

    """

    def _subclass(types: type | tuple[type | TypeVar, ...]):
        """Create a subclass of cls with generic parameters applied."""
        nonlocal cls
        all_annotations = _get_type_hints(cls)
        unbound_class_attributes = set(all_annotations.keys()).difference(
            _get_class_attributes(cls)
        )
        annotations = {
            k: v for k, v in all_annotations.items() if k in unbound_class_attributes
        }
        if not isinstance(types, tuple):
            types = (types,)
        if TypeVar in (type(t) for t in types):
            return cls
        if len(unbound_class_attributes) != len(types):
            raise TypeError(
                f"for {cls}, expected {len(unbound_class_attributes)} parameter(s), got {len(types)} parameter(s)."
            )
        return type(
            f"{cls.__name__}[{','.join(t.__name__ for t in types)}]",
            (cls,),
            {
                k: dict(zip(cls.__parameters__, types, strict=True))[  # type: ignore
                    v.__parameters__[0]
                ]
                for k, v in annotations.items()
            },
        )

    if not hasattr(cls, "__parameters__"):
        raise TypeError(f"Cannot decorate non-generic class '{cls.__name__}'")

    cls.__class_getitem__ = cache(_subclass)  # type: ignore
    return cls
