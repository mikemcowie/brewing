"""Renderers: translate endpoint return values into fastapi-compatible return values."""

from __future__ import annotations

import os
import random
import string
import sys
from abc import abstractmethod
from collections import ChainMap
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
    TypedDict,
    Unpack,
    cast,
    get_type_hints,
)

from pydantic import BaseModel, create_model
from sqlalchemy.orm import DeclarativeBase
from starlette import responses

from brewing.http import ViewSet, root, status, testing
from brewing.http.serialization.base import Renderer

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable, Mapping, Sequence

    from pydantic.config import ExtraValues
    from starlette.background import BackgroundTask
    from starlette.datastructures import URL
    from starlette.types import Receive, Scope, Send


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
        fields: Sequence[Any] | None = None,
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
        self.attributes = cast(
            "dict[str, Any]",
            {
                name: self._load_attribute(cast("str", name))
                for name in ChainMap(*(t.__dict__ for t in self.internal_t.__mro__))  # pyright: ignore[reportArgumentType, reportUnknownVariableType]
            },
        )
        for k, v in list(self.attributes.items()):
            if v is None:
                self.attributes.pop(k)
        self.fields = tuple(self._load_fields(fields or list(self.attributes.keys())))
        super().__init__(**validate_args)

    def _load_fields(self, fields: Sequence[Any]) -> Generator[str]:
        for field in fields:
            if isinstance(field, str):
                if hasattr(self.internal_t, field):
                    yield field
                    continue
                raise TypeError(f"No field {field} in {self.internal_t}")
            for key, value in self.attributes.items():
                if value is field:
                    yield key
                    continue
            raise TypeError(f"object {field} is not an attribute of {self.internal_t}")

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
        return create_model(
            self.schema_name,
            **{f: self.attributes[f] for f in self.attributes if f in self.fields},
        )


class BrewingResponse[InternalT: Any, WrapsT: responses.Response](responses.Response):
    """Brewing's wrapper around starlette Response classes.

    It inherits from and offers the same API as a starlette response,
    just with additional static generic type parameters.
    """

    wraps: type[WrapsT]
    internal_t: type[InternalT]

    def __init__(
        self,
        content: InternalT = None,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        self._wrapped = self.wraps(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type or self.wraps.media_type,
            background=background,
        )

    def __getattr__(self, name: Any):
        return getattr(self._wrapped, name)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        return await self._wrapped(scope, receive, send)


class PlainTextResponse(BrewingResponse[str, responses.PlainTextResponse]):
    wraps = responses.PlainTextResponse


type JSONCompatible = (
    dict[str, float | str | None | list[JSONCompatible]] | list[JSONCompatible]
)


class JSONResponse(BrewingResponse[JSONCompatible, responses.JSONResponse]):
    wraps = responses.JSONResponse


class HTMLResponse(BrewingResponse[str, responses.HTMLResponse]):
    wraps = responses.HTMLResponse


class RedirectResponse(BrewingResponse[str, responses.RedirectResponse]):
    wraps = responses.RedirectResponse

    def __init__(
        self,
        url: str | URL,
        status_code: int = 307,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
    ):
        self._wrapped = self.wraps(
            url=url,
            status_code=status_code,
            headers=headers,
            background=background,
        )


class StreamingResponse[InternalT: Any](
    BrewingResponse[InternalT, responses.StreamingResponse]
):
    wraps = responses.StreamingResponse


class FileResponse(BrewingResponse[os.PathLike[str], responses.FileResponse]):
    wraps = responses.FileResponse

    def __init__(  # noqa: PLR0913
        self,
        path: str | os.PathLike[str],
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
        filename: str | None = None,
        stat_result: os.stat_result | None = None,
        method: str | None = None,
        content_disposition_type: str = "attachment",
    ):
        self._wrapped = self.wraps(
            path=path,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
            filename=filename,
            stat_result=stat_result,
            method=method,
            content_disposition_type=content_disposition_type,
        )


class TestBrewingResponse:
    class ResponseTypeTestViews(ViewSet):
        # Random bytes to test the streaming response with.
        random_bytes = random.randbytes(1024)
        random_string = "".join(random.choice(string.ascii_letters) for _ in range(100))

        @root("text").GET()
        async def text(self):
            return PlainTextResponse(content="foo")

        @root("json").GET()
        async def json(self):
            return JSONResponse(content={"foo": "bar"})

        @root("html").GET()
        async def html(self):
            return HTMLResponse(content="<html></html>")

        @root("redirect").GET()
        async def redirect(self):
            return RedirectResponse("/html")

        @root("stream").GET()
        def stream(self):
            def iterbytes():
                with TemporaryDirectory(delete=False) as temp:
                    source_file = Path(temp) / "file"
                    source_file.write_bytes(self.random_bytes)
                    with source_file.open("br") as f:
                        yield from f

            iterator = iterbytes()
            return StreamingResponse(iterator)

        @root("file").GET()
        def file(self):
            with TemporaryDirectory(delete=False) as temp:
                source_file = Path(temp) / "file"
                source_file.write_text(self.random_string)

            return FileResponse(source_file)

    def client(self):
        return testing.new_client(self.ResponseTypeTestViews())

    def test_plain(self):
        result = self.client().get("/text")
        assert result.status_code == status.HTTP_200_OK
        assert result.text == "foo"
        assert result.headers.get("content-type") == "text/plain; charset=utf-8"

    def test_json(self):
        result = self.client().get("/json")
        assert result.status_code == status.HTTP_200_OK
        assert result.json() == {"foo": "bar"}
        assert result.headers.get("content-type") == "application/json"

    def test_html(self):
        result = self.client().get("/html")
        assert result.status_code == status.HTTP_200_OK
        assert result.text == "<html></html>"
        assert result.headers.get("content-type") == "text/html; charset=utf-8"

    def test_redirect(self):
        result = self.client().get("/redirect", follow_redirects=False)
        assert result.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert result.headers.get("location") == "/html"
        result_following_redirect = self.client().get(
            "/redirect", follow_redirects=True
        )
        assert result_following_redirect.status_code == status.HTTP_200_OK
        assert result_following_redirect.text == "<html></html>"
        assert (
            result_following_redirect.headers.get("content-type")
            == "text/html; charset=utf-8"
        )

    def test_stream(self):
        with self.client().stream("GET", "/stream") as stream:
            result = stream.read()
        assert result == self.ResponseTypeTestViews.random_bytes

    def test_file(self):
        result = self.client().get("/file")
        assert result.status_code == status.HTTP_200_OK
        assert result.text == self.ResponseTypeTestViews.random_string
