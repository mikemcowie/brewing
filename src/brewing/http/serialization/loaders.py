"""Loader: produce an external model that will serialize to an internal model."""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from types import FunctionType, MethodType
from typing import TYPE_CHECKING, Any, Self, get_type_hints

from pydantic import BaseModel, create_model
from sqlalchemy.orm import DeclarativeBase

if TYPE_CHECKING:
    from collections.abc import Callable


class Loader[InputT, InternalT](ABC):
    """Convert an object from the form fastapi loaded from the request, into the form annotated on the endpoint."""

    model: type[InputT]

    @abstractmethod
    def load(self, obj: InputT) -> InternalT:
        """Load given input model instance to interal representation."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class TypeLoader[InternalT](Loader[BaseModel, InternalT]):
    @staticmethod
    def _load_from_type(internal_t: type):
        _internal_t = internal_t
        _factory = internal_t.__init__
        if not isinstance(_factory, FunctionType):
            raise TypeError(
                f"class {internal_t} does not have an __init__ method and hence cannot be used here."
            )
        return _internal_t, _factory

    @staticmethod
    def _load_from_function(internal_t: FunctionType):
        try:
            return_annotation = get_type_hints(internal_t)["return"]
        except KeyError as error:
            raise TypeError(
                f"function {internal_t} does not have a return annotation and hence cannot be used in this context."
            ) from error
        if not isinstance(return_annotation, type):
            raise TypeError(
                f"return annotation of {internal_t}, {return_annotation} is not a type"
            )
        return return_annotation, internal_t

    @staticmethod
    def _load_from_classmethod(internal_t: MethodType):
        return_annotation = get_type_hints(internal_t).get("return")
        if return_annotation is not Self and not isinstance(return_annotation, type):  # pyright: ignore[reportGeneralTypeIssues]
            raise TypeError(
                "Cannot use a classmethod to find the type unless it is annotated with return type Self."
            )
        if return_annotation is Self:  # pyright: ignore[reportGeneralTypeIssues]
            return_annotation = internal_t.__self__
        if not isinstance(return_annotation, type):
            raise TypeError(
                f"method {internal_t.__name__} cannot be used unless it is a classmethod."
            )
        return return_annotation, internal_t

    def _validate_untyped_params(self):
        _untyped_params = set(self._signature.parameters.keys()).difference(
            self._type_hints
        )
        parameter_kinds = {
            name: parameter.kind
            for name, parameter in list(self._signature.parameters.items())[1:]
        }

        if _untyped_params:
            # The first paramter if allowed to be untyped, to allow for 'self' / 'cls' parameters
            # which conventionally are not type hinted.
            first_parameter = next(iter(self._signature.parameters.keys()))
            if first_parameter in _untyped_params:
                _untyped_params.remove(first_parameter)
        if _untyped_params:
            raise TypeError(
                f"Missing type parameters for {self._factory.__module__}:{self._factory.__qualname__}: {_untyped_params}"
            )
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

    def _load_type_hints(self):
        if (
            issubclass(self._internal_t, DeclarativeBase)
            and self._factory is self._internal_t.__init__
            and self._factory is not DeclarativeBase.__init__
        ):
            # sqlalchemy creates a wrapping __init__ method, we can only access the attributes of the original factory
            # by inspecting an internal attibute.
            return get_type_hints(
                self._internal_t.__init__._sa_original_init  # noqa: SLF001 # type: ignore
            )
        else:
            return get_type_hints(self._factory)

    def _load_type_and_factory(
        self, internal_t: Callable[..., InternalT]
    ) -> tuple[type, FunctionType | MethodType]:
        if isinstance(internal_t, type):
            return self._load_from_type(internal_t)
        elif isinstance(internal_t, FunctionType):
            return self._load_from_function(internal_t)
        # We can also use a classmethod annotated with return type "Self".
        elif isinstance(internal_t, MethodType):
            return self._load_from_classmethod(internal_t)
        else:
            raise TypeError(
                f"{internal_t} is neither a class nor a function and hence cannot be used in this context."
            )

    def __init__(
        self,
        internal_t: Callable[..., InternalT],
        schema_name: str | Callable[[type[Any]], str] = lambda n: n.__name__,
    ) -> None:
        self._internal_t, self._factory = self._load_type_and_factory(internal_t)
        self._schema_name = (
            schema_name
            if isinstance(schema_name, str)
            else schema_name(self._internal_t)
        )
        self._signature = inspect.signature(self._factory)
        self._type_hints = self._load_type_hints()
        self._validate_untyped_params()
        self.model = self._create_model()

    def _create_model(self) -> type[BaseModel]:
        """The pydantic model generated based on the internal model."""
        type_hints = self._type_hints.copy()
        type_hints.pop("return", None)
        return create_model(self._schema_name, **type_hints)

    def load(self, obj: BaseModel) -> InternalT:
        data = obj.model_dump()
        return self._internal_t(**data)
