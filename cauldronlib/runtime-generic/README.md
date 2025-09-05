# runtime-generic

Decorator that makes some class's generic be able to be instantiated.

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
