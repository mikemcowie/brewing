"""Loader: produce an external model that will serialize to an internal model."""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from functools import cached_property
from types import FunctionType
from typing import TYPE_CHECKING, get_type_hints

from pydantic import BaseModel, create_model
from sqlalchemy.orm import DeclarativeBase

if TYPE_CHECKING:
    from collections.abc import Callable


class Loader[InputT, InternalT](ABC):
    """Convert an object from the form fastapi loaded from the request, into the form annotated on the endpoint."""

    @abstractmethod
    def load(self, obj: InputT) -> InternalT:
        """Load given input model instance to interal representation."""
        ...


class TypeLoader[InternalT](Loader[BaseModel, InternalT]):
    def __init__(self, internal_t: Callable[..., InternalT]) -> None:
        if isinstance(internal_t, type):
            self._internal_t = internal_t
            self._factory = internal_t.__init__
            if not isinstance(self._factory, FunctionType):
                raise TypeError(
                    f"class {internal_t} does not have an __init__ method and hence cannot be used here."
                )
        elif isinstance(internal_t, FunctionType):
            try:
                return_annotation = get_type_hints(self._internal_t)["return"]
            except KeyError as error:
                raise TypeError(
                    f"function {internal_t} does not have a return annotation and hence cannot be used in this context."
                ) from error
            if not isinstance(return_annotation, type):
                raise TypeError(
                    f"return annotation of {self._internal_t}, {return_annotation} is not a type"
                )
            self._internal_t = return_annotation
        else:
            raise TypeError(
                f"{internal_t} is neither a class nor a function and hence cannot be used in this context."
            )
        self._signature = inspect.signature(self._factory)

        self._type_hints = get_type_hints(self._factory)
        if (
            issubclass(self._internal_t, DeclarativeBase)
            and self._factory is self._internal_t.__init__
            and self._factory is not DeclarativeBase.__init__
        ):
            # sqlalchemy creates a wrapping __init__ method, we can only access the attributes of the original factory
            # by inspecting an internal attibute.
            self._type_hints = get_type_hints(
                self._internal_t.__init__._sa_original_init  # noqa: SLF001 # type: ignore
            )

        self._untyped_params = set(self._signature.parameters.keys()).difference(
            self._type_hints
        )
        if self._untyped_params:
            # The first paramter if allowed to be untyped, to allow for 'self' / 'cls' parameters
            # which conventionally are not type hinted.
            first_parameter = next(iter(self._signature.parameters.keys()))
            if first_parameter in self._untyped_params:
                self._untyped_params.remove(first_parameter)
            if self._untyped_params:
                raise TypeError(
                    f"Missing type parameters for {self._factory.__module__}:{self._factory.__qualname__}: {self._untyped_params}"
                )
        parameter_kinds = {
            name: parameter.kind
            for name, parameter in list(self._signature.parameters.items())[1:]
        }
        if (
            inspect.Parameter.POSITIONAL_ONLY in parameter_kinds.values()
            or inspect.Parameter.VAR_POSITIONAL in parameter_kinds.values()
        ):
            raise TypeError("Cannot process factory with positional-only parameters.")
        if {inspect.Parameter.VAR_KEYWORD} == {*parameter_kinds.values()}:
            raise TypeError(
                "function must accept at least 1 named keyword argument"
                " (not **kwargs) in  __init__."
            )

    @cached_property
    def model(self) -> type[BaseModel]:
        """The pydantic model generated based on the internal model."""
        return create_model("", **{})

    def load(self, obj: BaseModel) -> InternalT:
        return self._internal_t(**obj.model_dump())
