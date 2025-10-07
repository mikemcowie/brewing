"""Unit tests for annotations."""

from __future__ import annotations
from typing import Annotated, get_type_hints, Any, Callable
from collections.abc import Sequence
from types import FunctionType
from dataclasses import dataclass, replace
import pytest
import inspect

ob1 = object()
ob2 = object()


type AnnotatedFunctionAdaptor = Callable[[_AnnotationState], _AnnotationState]
type AnnotatedFunctionAdaptorPipeline = Sequence[AnnotatedFunctionAdaptor]

_ADAPTOR_KEY = "_brewing_adaptor"


@dataclass(frozen=True)
class _Annotation:
    """Struct representing a single annotation"""

    type_: Any
    annotated: tuple[Any, ...] | None

    def raw(self) -> Any:
        """Returns the annotation in the form used in __annotations__"""
        if self.annotated:
            return Annotated[self.type_, self.annotated]
        else:
            return self.type_


class _AnnotationState:
    """Mutable data structure processed in 'adapted()' by a sequence of adaptors."""

    def __init__(self, func: FunctionType, /, **kwargs: _Annotation):
        self.func = func
        self.kwargs = kwargs

    def apply(self):
        """Apply the current state of the annotations to the function."""
        for key, value in self.kwargs.items():
            self.func.__annotations__[key] = value.raw()


def capture(func: FunctionType) -> _AnnotationState:
    hints: dict[str, _Annotation] = {}
    # first we capture annotations with get_type_hints
    for name, hint in get_type_hints(func, include_extras=True).items():
        if metadata := getattr(hint, "__metadata__", None):
            hints[name] = _Annotation(getattr(hint, "__origin__"), metadata)
        else:
            hints[name] = _Annotation(hint, None)
    # get_type_hints doesn't tell us about any unannotated parameters,
    # so we use inspect.signature to find those
    inspect_params = inspect.signature(func).parameters
    for name, parameter in inspect_params.items():
        if name not in hints:
            # assumption - inspect.signature should only return untyped parameters here.
            # so incase that assumption is wrong, catch it.
            if parameter.annotation is not inspect.Parameter.empty:
                raise RuntimeError(
                    f"unexpected: parameter {name} is annotated according to inspect.signature, "
                    "but not according to typing.get_type_hints."
                )
            hints[name] = _Annotation(inspect.Parameter.empty, None)

    return _AnnotationState(func, **hints)


def adapt(
    func: FunctionType, pipeline: AnnotatedFunctionAdaptorPipeline
) -> FunctionType:
    """Return an adapted version of a function, by applying a pipeline of adaptors.

    The returned function could be:
    * the same function that was passed in with inplace annotations
    * a wrapping or decorating function
    * (though not intended) could be an entirely different function.

    Args:
        func (FunctionType): The input function to enter the first item of the pipeline
        pipeline (AnnotatedFunctionAdaptorPipeline): A seequence of callables,
           each taking and returning a CapturedAnnotations object.
    """
    captured = capture(func)
    for adaptor in pipeline:
        if not hasattr(adaptor, _ADAPTOR_KEY):
            raise TypeError(
                f"{adaptor=} needs to be decorated with brewing.http.annotations.adaptor"
            )
        captured = adaptor(captured)
    captured.apply()
    return captured.func


def adaptor(func: AnnotatedFunctionAdaptor):
    """Mark function as an adaptor.

    Intended to be used as a decorator. It must be applied to any function
    in order for that function to be usable in a pipeline for adapt().

    It adds metadata to the function, without which the function will not be
    allowed to be used in adapted.

    Though making no runtime change to the function's behaviour, this ensures
    type-checkers can detect functions tht don't match the needed signature
    of the pipeline functions
    """
    setattr(func, _ADAPTOR_KEY, True)
    return func


def some_func(self, foo: str, bar: Annotated[int, ob1]) -> Annotated[float, (ob1, ob2)]:
    """Just a random function."""
    return (len(foo) + bar) / 2


def test_capture_annotation():
    assert capture(some_func).kwargs == {
        "self": _Annotation(inspect.Parameter.empty, None),
        "foo": _Annotation(str, None),
        "bar": _Annotation(int, (ob1,)),
        "return": _Annotation(float, ((ob1, ob2),)),
    }


def test_adaptor_pipeline():
    def adaptee(foo) -> str:
        return "bar"

    @adaptor
    def all_unannotated_as_any(annotations: _AnnotationState) -> _AnnotationState:
        """Any unannoted parameter gets typing.Any applied."""
        for key, value in annotations.kwargs.items():
            if value.type_ is inspect.Parameter.empty:
                annotations.kwargs[key] = replace(value, type_=Any)
        return annotations

    # Give a function with an unannotated paramter
    assert capture(adaptee).kwargs == {
        "foo": _Annotation(inspect.Parameter.empty, None),
        "return": _Annotation(str, None),
    }
    # If we call adapt with a pipeline containing a function that adapts it to
    # add the Any annotation
    result = adapt(adaptee, [all_unannotated_as_any])
    # Given that the all_unannoted_as_any returns the same function that was passed
    # It should be the same object
    assert result is adaptee
    # But the annotation should have changed.
    assert capture(adaptee).kwargs == {
        "foo": _Annotation(Any, None),
        "return": _Annotation(str, None),
    }


def test_adaptor_pipeline_fails_if_pipeline_func_is_not_decorated():
    def adaptee(foo) -> str:
        return "bar"

    def all_unannotated_as_any(annotations: _AnnotationState) -> _AnnotationState:
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
