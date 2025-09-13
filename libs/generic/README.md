1-line decorator to allow a class to be subclassed via generic syntax.

Specifically limited to the pattern where:

1. a class variable is declared, unbound, as type[T], where T is a generic class parameter.
2. An arbitary amount of such type parameters can be handled.

# Example

```python
from brewinglib.generic import runtime_generic

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
