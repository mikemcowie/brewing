from __future__ import annotations

from typing import Literal

import pytest
from cauldron.runtime_generic import runtime_generic


class Someclass:
    pass


class SomeSubClass(Someclass):
    extra_attribute: Literal["foo"] = "foo"


@runtime_generic("generic_type")
class GenericThing[ModelT: Someclass]:
    generic_type: type[ModelT]


def test_runtime_generic_decorator():
    assert GenericThing[Someclass]().generic_type is Someclass, (
        "failed to create correct concrete subclass"
    )
    assert GenericThing[SomeSubClass]().generic_type is SomeSubClass, (
        "failed to create correct concrete subclass"
    )
    assert GenericThing[Someclass] is GenericThing[Someclass], (
        "subsequent calls should be cached"
    )
    assert GenericThing[SomeSubClass]().generic_type.extra_attribute == "foo"


def test_cant_use_decorator_on_class_that_already_has_class_setitem():
    with pytest.raises(RuntimeError) as err:

        @runtime_generic("foo")
        @runtime_generic("foo")
        class Foo:  # type: ignore
            pass

    assert (
        "Cannot decorate a class with runtime_generic more than once." in err.exconly()
    )
