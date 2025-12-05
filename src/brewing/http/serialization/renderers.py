"""Renderers: translate endpoint return values into fastapi-compatible return values."""

from __future__ import annotations

import sys
from abc import abstractmethod
from collections import ChainMap
from typing import TYPE_CHECKING, Any, Protocol, TypedDict, Unpack, cast, get_type_hints

from pydantic import BaseModel, create_model
from sqlalchemy.orm import DeclarativeBase

from brewing.http.serialization.base import Renderer

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from pydantic.config import ExtraValues


class NoopRenderer[T](Renderer[T, T]):
    """A renderer for when we don't need to render anything.

    This is a the right renderer to use if:

    * You are already returning a starlette Response object
      from the endpoint function.
    * You are returning a value that fastapi would already handle
      and you need no extra rendering or content negotiation.

    It's assumed if returning this type that the response type
    is application/json . Subclass this if you need something else.
    """

    content_type = "application/json"

    def __call__(self, obj: T, /) -> T:
        return obj


class PydanticValidateArgs(TypedDict, total=False):
    strict: bool | None
    extra: ExtraValues | None
    from_attributes: bool | None
    context: Any | None
    by_alias: bool | None
    by_name: bool | None


class BasePydanticRenderer[InternalT, ModelT: BaseModel](Renderer[InternalT, ModelT]):
    """Render objects to a pydantic model.

    Since fastapi natively uses pydantic, this base renderer is likely to be appropriate
    for returning JSON the majority of the time
    """

    content_type = "application/json"

    def __init__(self, **validate_args: Unpack[PydanticValidateArgs]) -> None:
        self.validate_args = validate_args

    @abstractmethod
    def create_model(self) -> type[ModelT]:
        """Return the model type that will be rendered to."""
        ...

    def __call__(
        self, obj: InternalT, /, **validate_args: Unpack[PydanticValidateArgs]
    ) -> ModelT:
        return self.create_model().model_validate(
            obj, **self.validate_args | validate_args
        )


class SimpleRenderer[ModelT: BaseModel](BasePydanticRenderer[object, ModelT]):
    """A renderer where the output model is defined as part of the contructor."""

    content_type = "application/json"

    def __init__(
        self, model: type[ModelT], **validate_args: Unpack[PydanticValidateArgs]
    ) -> None:
        self.model = model
        super().__init__(**validate_args)

    def create_model(self) -> type[ModelT]:
        return self.model


class _AttributeLoaderProtocol(Protocol):
    def __call__(self, name: str) -> type[Any] | None: ...


class SQLAlchemyORMRenderer[InternalT: DeclarativeBase](
    BasePydanticRenderer[InternalT, BaseModel]
):
    def __init__(
        self,
        internal_t: type[InternalT],
        schema_name: str | Callable[[type[Any]], str],
        load_relationshps: bool = True,
        /,
        **validate_args: Unpack[PydanticValidateArgs],
    ) -> None:
        self.internal_t = internal_t
        self.load_relationships = load_relationshps
        if callable(schema_name):
            self.child_schema_name_callable = schema_name
            self.schema_name = schema_name(self.internal_t)
        else:
            self.child_schema_name_callable = None
            self.schema_name = schema_name

        super().__init__(**validate_args)

    def _attribute_loaders(self) -> Iterable[_AttributeLoaderProtocol]:
        return (
            self._load_mapped_column,
            self._load_relationship,
            self._load_property,
        )

    def _load_property(self, name: str) -> type[Any] | None:
        attr = getattr(self.internal_t, name)
        if not isinstance(attr, property):
            raise TypeError
        return get_type_hints(attr.fget).get("return")

    def _load_mapped_column(self, name: str) -> type[Any]:
        # Don't load the column that is a foreign key if we are not loading relationships
        if not self.load_relationships and getattr(self.internal_t, name).foreign_keys:
            raise AttributeError()
        return getattr(self.internal_t, name).type.python_type

    def _load_relationship(self, name: str) -> type[Any]:
        if not self.load_relationships:
            raise AttributeError()
        collection_cls = getattr(self.internal_t, name).property.collection_class
        arg = getattr(
            sys.modules[self.internal_t.__module__],
            getattr(self.internal_t, name).property.argument,
        )
        arg_model = self.__class__(
            arg, self.child_schema_name_callable or arg.__name__, False
        ).create_model()

        if collection_cls:
            return collection_cls[arg_model]
        return arg_model

    def _load_attribute(self, name: str):
        for loader in self._attribute_loaders():
            try:
                return loader(name)
            except AttributeError, TypeError:
                pass

    def create_model(self) -> type[BaseModel]:
        attributes = cast(
            "dict[str, Any]",
            {
                name: self._load_attribute(cast("str", name))
                for name in ChainMap(*(t.__dict__ for t in self.internal_t.__mro__))  # pyright: ignore[reportArgumentType, reportUnknownVariableType]
            },
        )
        return create_model(
            self.schema_name, **{k: v for k, v in attributes.items() if v}
        )
