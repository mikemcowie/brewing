"""Renderers: translate endpoint return values into fastapi-compatible return values."""
from __future__ import annotations
from abc import abstractmethod
from typing import TypedDict, Any, Unpack
from brewing.http.serialization.base import Renderer
from pydantic import BaseModel
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



class BasePydanticRenderer[InternalT, ModelT:BaseModel](Renderer[InternalT, ModelT]):
    """Render objects to a pydantic model.
    
    Since fastapi natively uses pydantic, this is the base renderer likely to be used
    the majority of the time.
    """
    def __init__(self, **validate_args:Unpack[PydanticValidateArgs]) -> None:
        self.validate_args = validate_args

    @abstractmethod
    def get_model(self)->type[ModelT]:
        """Return the model type that will be rendered to."""
        ...

    def __call__(self, obj: InternalT, /, **validate_args:Unpack[PydanticValidateArgs]) -> ModelT:
        return self.get_model().model_validate(obj, **self.validate_args | validate_args)
    

class SimpleRenderer[ModelT:BaseModel](BasePydanticRenderer[object, ModelT]):
    """A renderer where the output model is defined as part of the contructor."""

    content_type = "application/json"

    def __init__(self, model:type[ModelT], **validate_args: Unpack[PydanticValidateArgs]) -> None:
        self.model = model
        super().__init__(**validate_args)

    def get_model(self) -> type[ModelT]:
        return self.model
    


from sqlalchemy.orm import DeclarativeBase


import dataclasses
import pytest
from pydantic import ValidationError
from types import SimpleNamespace as SN



class TestSimpleRenderer:

    class DataModel(BaseModel):
        foo:str
        bar:int

    def get_renderer(self, **kwargs:Unpack[PydanticValidateArgs]):
        return SimpleRenderer(self.DataModel, **kwargs)
    

    def test_raises_missing_attr(self):
        renderer = self.get_renderer(from_attributes=True)
        with pytest.raises(ValidationError):
            renderer(object())

    def test_raises_from_attributes_false(self):
        renderer = self.get_renderer(from_attributes=False)
        with pytest.raises(ValidationError):
            renderer(SN(foo="v1", bar=1))

    def test_renders_from_attributes(self):
        renderer = self.get_renderer(from_attributes=True)
        assert renderer(SN(foo="v1", bar=1)) == self.DataModel(foo="v1", bar=1)

    def test_renders_dict(self):
        renderer = self.get_renderer(from_attributes=False)
        assert renderer({"foo": "v1", "bar": 1}) == self.DataModel(foo="v1", bar=1)