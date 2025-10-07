"""Utilities for managing and rewriting annotations."""

from __future__ import annotations
from typing import Annotated, get_type_hints, Any, Callable
from collections.abc import Sequence
from types import FunctionType
from dataclasses import dataclass
import inspect

ob1 = object()
ob2 = object()


type AnnotatedFunctionAdaptor = Callable[[AnnotationState], AnnotationState]
type AnnotatedFunctionAdaptorPipeline = Sequence[AnnotatedFunctionAdaptor]

_ADAPTOR_KEY = "_brewing_adaptor"


@dataclass(frozen=True)
class Annotation:
    """Struct representing a single annotation."""

    type_: Any
    annotated: tuple[Any, ...] | None

    def raw(self) -> Any:
        """Return the annotation in the form used in __annotations__."""
        if self.annotated:
            return Annotated[self.type_, self.annotated]
        else:
            return self.type_


class AnnotationState:
    """Mutable data structure processed in 'adapted()' by a sequence of adaptors."""

    def __init__(self, func: FunctionType, /, **kwargs: Annotation):
        self.func = func
        self.kwargs = kwargs

    def apply(self):
        """Apply the current state of the annotations to the function."""
        for key, value in self.kwargs.items():
            self.func.__annotations__[key] = value.raw()


def capture(func: FunctionType) -> AnnotationState:
    """Capture the state of annotations on a function."""
    hints: dict[str, Annotation] = {}
    # first we capture annotations with get_type_hints
    for name, hint in get_type_hints(func, include_extras=True).items():
        if metadata := getattr(hint, "__metadata__", None):
            hints[name] = Annotation(getattr(hint, "__origin__"), metadata)
        else:
            hints[name] = Annotation(hint, None)
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
            hints[name] = Annotation(inspect.Parameter.empty, None)

    return AnnotationState(func, **hints)


def adapt(
    func: FunctionType, pipeline: AnnotatedFunctionAdaptorPipeline
) -> FunctionType:
    """
    Return an adapted version of a function, by applying a pipeline of adaptors.

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
    """
    Mark function as an adaptor.

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
