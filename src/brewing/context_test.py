"""Unit tests for context module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from brewing import context

if TYPE_CHECKING:
    from pytest_subtests import SubTests


class _SomeSubclass1(context.HasGlobalContext):
    pass


class _SomeSubclass2(context.HasGlobalContext):
    pass


def test_subclass_contextholding_creates_new_contextvar():
    """All subckasses of ContextHolding will create a distinct classvar."""

    assert context.HasGlobalContext.current is not _SomeSubclass1.current
    assert context.HasGlobalContext.current is not _SomeSubclass2.current


def test_push_and_current(subtests: SubTests):
    i1 = _SomeSubclass1()
    i2 = _SomeSubclass2()

    with subtests.test("default-unset-state-raises"):
        with pytest.raises(context.ContextNotAvailable):
            context.current(_SomeSubclass1)

        with pytest.raises(context.ContextNotAvailable):
            context.current(_SomeSubclass2)

    with subtests.test("one-pushed-other-raises"), context.push(i1):
        assert context.current(_SomeSubclass1) is i1

        with pytest.raises(context.ContextNotAvailable):
            context.current(_SomeSubclass2)

    with subtests.test("reset-both-raise"):
        with pytest.raises(context.ContextNotAvailable):
            context.current(_SomeSubclass1)

        with pytest.raises(context.ContextNotAvailable):
            context.current(_SomeSubclass2)

    with subtests.test("both-pushed"), context.push(i1, i2):
        assert context.current(_SomeSubclass1) is i1
        assert context.current(_SomeSubclass2) is i2

    with subtests.test("reset-both-raise-2"):
        with pytest.raises(context.ContextNotAvailable):
            context.current(_SomeSubclass1)

        with pytest.raises(context.ContextNotAvailable):
            context.current(_SomeSubclass2)

    with subtests.test("other-pushed"), context.push(i2):
        with pytest.raises(context.ContextNotAvailable):
            context.current(_SomeSubclass1)
        assert context.current(_SomeSubclass2) is i2
