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
    assert GenericThing[Someclass]().generic_type is Someclass, GenericThing[
        Someclass
    ]().generic_type
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


@runtime_generic("")
class HasOneParam[T1]:
    t1: type[T1]


@runtime_generic("")
class HasTwoParam[T1, T2]:
    t1: type[T1]
    t2: type[T2]


@runtime_generic("")
class HasThreeParam[T1, T2, T3]:
    t1: type[T1]
    t2: type[T2]
    t3: type[T3]


def test_cannot_pass_wrong_number_of_params():
    with pytest.raises(TypeError) as err:
        HasOneParam[object, object]  # type: ignore
    assert "expected 1 parameter(s), got 2 parameter(s)." in err.exconly()

    with pytest.raises(TypeError) as err:
        HasTwoParam[object]  # type: ignore
    assert "expected 2 parameter(s), got 1 parameter(s)." in err.exconly()

    with pytest.raises(TypeError) as err:
        HasTwoParam[object, object, object]  # type: ignore
    assert "expected 2 parameter(s), got 3 parameter(s)." in err.exconly()

    with pytest.raises(TypeError) as err:
        HasThreeParam[object]  # type: ignore
    assert "expected 3 parameter(s), got 1 parameter(s)." in err.exconly()

    with pytest.raises(TypeError) as err:
        HasThreeParam[object, object]  # type: ignore
    assert "expected 3 parameter(s), got 2 parameter(s)." in err.exconly()
