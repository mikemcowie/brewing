"""Unit tests for annotations."""

from __future__ import annotations
from typing import Annotated, Any
from dataclasses import replace
import pytest
import inspect
from brewing.http.annotations import (
    capture,
    Annotation,
    AnnotationState,
    adapt,
    adaptor,
)

ob1 = object()
ob2 = object()

_ADAPTOR_KEY = "_brewing_adaptor"


def some_func(self, foo: str, bar: Annotated[int, ob1]) -> Annotated[float, (ob1, ob2)]:
    """Just a random function."""
    return (len(foo) + bar) / 2


def test_capture_annotation():
    assert capture(some_func).kwargs == {
        "self": Annotation(inspect.Parameter.empty, None),
        "foo": Annotation(str, None),
        "bar": Annotation(int, (ob1,)),
        "return": Annotation(float, ((ob1, ob2),)),
    }


def test_adaptor_pipeline():
    def adaptee(foo) -> str:
        return "bar"

    @adaptor
    def all_unannotated_as_any(annotations: AnnotationState) -> AnnotationState:
        """Any unannoted parameter gets typing.Any applied."""
        for key, value in annotations.kwargs.items():
            if value.type_ is inspect.Parameter.empty:
                annotations.kwargs[key] = replace(value, type_=Any)
        return annotations

    # Give a function with an unannotated paramter
    assert capture(adaptee).kwargs == {
        "foo": Annotation(inspect.Parameter.empty, None),
        "return": Annotation(str, None),
    }
    # If we call adapt with a pipeline containing a function that adapts it to
    # add the Any annotation
    result = adapt(adaptee, [all_unannotated_as_any])
    # Given that the all_unannoted_as_any returns the same function that was passed
    # It should be the same object
    assert result is adaptee
    # But the annotation should have changed.
    assert capture(adaptee).kwargs == {
        "foo": Annotation(Any, None),
        "return": Annotation(str, None),
    }


def test_adaptor_pipeline_fails_if_pipeline_func_is_not_decorated():
    def adaptee(foo) -> str:
        return "bar"

    def all_unannotated_as_any(annotations: AnnotationState) -> AnnotationState:
        """Any unannoted parameter gets typing.Any applied."""
        for key, value in annotations.kwargs.items():
            if value.type_ is inspect.Parameter.empty:
                annotations.kwargs[key] = replace(value, type_=Any)
        return annotations

    with pytest.raises(TypeError) as error:
        adapt(adaptee, [all_unannotated_as_any])
    assert (
        "needs to be decorated with brewing.http.annotations.adaptor" in error.exconly()
    )
