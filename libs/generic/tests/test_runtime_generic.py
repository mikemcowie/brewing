from __future__ import annotations

from typing import ClassVar, Literal

import pytest
from brewinglib.generic import runtime_generic


class Someclass:
    pass


class SomeSubClass(Someclass):
    extra_attribute: Literal["foo"] = "foo"


@runtime_generic
class GenericThing[ModelT: Someclass]:
    generic_type: type[ModelT]

    def __init__(self):
        self.generic_instance = self.generic_type()

    def do_something(self) -> str:
        return str(self.generic_instance)


@runtime_generic
class HasOneParam[T1]:
    t1: type[T1]


@runtime_generic
class HasTwoParam[T1, T2]:
    t1: type[T1]
    t2: type[T2]


@runtime_generic
class HasThreeParam[T1, T2, T3]:
    t1: type[T1]
    t2: type[T2]
    t3: type[T3]


class A:
    pass


class B:
    pass


class C:
    pass


def test_adds_expected_attribute():
    assert GenericThing[Someclass]().generic_type is Someclass, GenericThing[
        Someclass
    ]().generic_type
    assert GenericThing[SomeSubClass]().generic_type is SomeSubClass, (
        "failed to create correct concrete subclass"
    )


def test_cache():
    assert GenericThing[Someclass] is GenericThing[Someclass], (
        "subsequent calls should be cached"
    )
    assert GenericThing[Someclass] is not GenericThing[SomeSubClass], (
        "different params should return different instances."
    )


def test_multiple_params():
    abc = HasThreeParam[A, B, C]()
    acb = HasThreeParam[A, C, B]()
    bac = HasThreeParam[B, A, C]()
    bca = HasThreeParam[B, C, A]()
    cab = HasThreeParam[C, A, B]()
    cba = HasThreeParam[C, B, A]()

    assert abc.t1 is A, abc.t1
    assert abc.t2 is B, abc.t2
    assert abc.t3 is C, abc.t3

    assert acb.t1 is A, acb.t1
    assert acb.t2 is C, acb.t2
    assert acb.t3 is B, acb.t2

    assert bac.t1 is B, bac.t1
    assert bac.t2 is A, bac.t2
    assert bac.t3 is C, bac.t3

    assert bca.t1 is B, bca.t1
    assert bca.t2 is C, bca.t2
    assert bca.t3 is A, bca.t3

    assert cab.t1 is C, cab.t1
    assert cab.t2 is A, cab.t2
    assert cab.t3 is B, cab.t3

    assert cba.t1 is C, cba.t1
    assert cba.t2 is B, cba.t2
    assert cba.t3 is A, bca.t3


def test_cannot_pass_wrong_number_of_params():
    # raise Exception(HasOneParam[A,B]())
    with pytest.raises(TypeError) as err:
        HasOneParam[A, B]  # type: ignore
    assert "expected 1 parameter(s), got 2 parameter(s)." in err.exconly()

    with pytest.raises(TypeError) as err:
        HasTwoParam[A]  # type: ignore
    assert "expected 2 parameter(s), got 1 parameter(s)." in err.exconly()

    with pytest.raises(TypeError) as err:
        HasTwoParam[A, B, C]  # type: ignore
    assert "expected 2 parameter(s), got 3 parameter(s)." in err.exconly()

    with pytest.raises(TypeError) as err:
        HasThreeParam[A]  # type: ignore
    assert "expected 3 parameter(s), got 1 parameter(s)." in err.exconly()

    with pytest.raises(TypeError) as err:
        HasThreeParam[A, B]  # type: ignore
    assert "expected 3 parameter(s), got 2 parameter(s)." in err.exconly()


def test_class_attributes_in_different_order_from_params():
    @runtime_generic
    class HasTwoParamsWithDifferentOrderOfClassAttr[T1, T2]:
        a: type[T2]
        b: type[T1]

    class A:
        a = "a"

    class B:
        b = "b"

    assert HasTwoParamsWithDifferentOrderOfClassAttr[A, B]().a.b
    assert HasTwoParamsWithDifferentOrderOfClassAttr[A, B]().b.a

    with pytest.raises(AttributeError):
        assert HasTwoParamsWithDifferentOrderOfClassAttr[A, B]().a.a  # type: ignore

    with pytest.raises(AttributeError):
        assert HasTwoParamsWithDifferentOrderOfClassAttr[A, B]().b.b  # type: ignore


def test_nongeneric_class():
    with pytest.raises(TypeError) as error:

        @runtime_generic
        class NonGeneric:  # type: ignore
            foo = "bar"

    assert "Cannot decorate non-generic class 'NonGeneric'" in error.exconly()


def test_with_other_class_attributes():
    @runtime_generic
    class HasOtherClassAttributes[T1, T2]:
        a: type[T1]
        b: type[T2]
        c: ClassVar[dict[str, str]] = {}

    # Test that other class attributes like
    # this mutable dictionary behaves as you would expect
    # through subclassing.
    assert HasOtherClassAttributes[A, B]().c == {}
    HasOtherClassAttributes[A, B]().c["foo"] = "bar"
    assert HasOtherClassAttributes[A, B]().c == {"foo": "bar"}
    # Given class attribute c is on the parent class
    # It is also shared by subclasses if they don't do anything
    # To change the situation.
    assert HasOtherClassAttributes[B, A]().c == {"foo": "bar"}
