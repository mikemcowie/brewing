"""Utilities for managing and rewriting annotations."""

from __future__ import annotations
from typing import Annotated, get_type_hints, Any, Protocol, TYPE_CHECKING, Callable
from fastapi import Depends
from abc import abstractmethod
from collections.abc import Sequence
from types import FunctionType
from dataclasses import dataclass
import inspect

if TYPE_CHECKING:
    from brewing.http import ViewSet


class AnnotatedFunctionAdaptor(Protocol):
    """Protocol for a callable that adapts a function's annotations."""

    @abstractmethod
    def __call__(self, state: AnnotationState) -> AnnotationState:
        """
        Adapt annotation state object.

        This is used in a pipeline of similar objects in 'adapt()'

        * The returned object may be the same as the input or different.
        * The function referred in the state object may be replaced.
        * The hints mapping in the returned object may be mutated.

        Hence to ensure predictability, it's recommended to use the returned object
        rather than assuming mutation of the input object.
        """
        ...


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
            return Annotated[self.type_, *self.annotated]
        else:
            return self.type_


class AnnotationState:
    """Facilty for loading the current state of a function's annotations and applying changes."""

    def __init__(
        self,
        func: FunctionType,
        /,
    ):
        self.func = func
        self.hints: dict[str, Annotation] = {}
        # first we capture annotations with get_type_hints
        for name, hint in get_type_hints(func, include_extras=True).items():
            if metadata := getattr(hint, "__metadata__", None):
                self.hints[name] = Annotation(getattr(hint, "__origin__"), metadata)
            else:
                self.hints[name] = Annotation(hint, None)
        # get_type_hints doesn't tell us about any unannotated parameters,
        # so we use inspect.signature to find those
        inspect_params = inspect.signature(func).parameters
        for name in inspect_params.keys():
            if name not in self.hints:
                self.hints[name] = Annotation(inspect.Parameter.empty, None)

    def abandon_pending(self):
        """Abandon/reset any changes and reset to the current state of the function's annotations."""
        self.__init__(self.func)

    def apply_pending(self):
        """Apply the current state of the annotations to the function."""
        for key, value in self.hints.items():
            try:
                self.func.__annotations__[key] = value.raw()
            except AttributeError:
                pass
        self.__init__(self.func)


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
    state = AnnotationState(func)
    for adaptor in pipeline:
        if not hasattr(adaptor, _ADAPTOR_KEY):
            raise TypeError(
                f"{adaptor=} needs to be decorated with brewing.http.annotations.adaptor"
            )
        state = adaptor(state)
        state.apply_pending()
    return state.func


def adaptor[T: Callable[..., Any]](func: T) -> T:
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


@adaptor
class ApplyViewSetDependency(AnnotatedFunctionAdaptor):
    """If first parameter of an viewset endpoint function is untyped, annotate it as the viewset."""

    def __init__(self, viewset: ViewSet):
        self.viewset = viewset

    def __call__(self, state: AnnotationState) -> AnnotationState:
        """Modify annotations of parameters should be a dependency on the viewset."""
        # late import to avoid circular dependency
        from brewing.http import ViewSet

        for key, value in state.hints.items():
            # A single unannotated parameter - typically, though not required to be
            # the first positional paramter, is turned into a dependency on the viewset.
            # This is to support the first parameter of a method (self) being automatically
            # set via dependency injection to the viewset in class-based endpoints.
            annotation = Annotation(
                type(self.viewset), (Depends(lambda: self.viewset),)
            )
            if value.type_ is inspect.Parameter.empty:
                state.hints[key] = annotation
                break
            # And anyting typed as the viewset type, or a superclass of it
            # that is also a subclass of ViewSet, also gets this setup.
            if any(
                (
                    (
                        isinstance(value.type_, type)
                        and issubclass(value.type_, ViewSet)
                    ),
                    value.type_ is type(self.viewset),
                    type(self.viewset) in getattr(value.type_, "__mro__", []),
                )
            ):
                state.hints[key] = annotation

        return state
