"""Utilities for constructing and validating HTTP paths."""

from __future__ import annotations
from dataclasses import dataclass
import re
from functools import partial
from types import EllipsisType
from typing import TYPE_CHECKING, Any, Callable, Literal
from fastapi import APIRouter
from brewing.http.endpoint_decorator import EndpointDecorator, DependencyDecorator
from brewing.http.annotations import AnnotatedFunctionAdaptorPipeline
from http import HTTPMethod


if TYPE_CHECKING:
    from brewing.http import ViewSet

    # We are making some fake assignments
    # so that the type checker will give better completions.
    r = APIRouter()
    GET = partial(r.get, "")
    POST = partial(r.post, "")
    PUT = partial(r.put, "")
    PATCH = partial(r.patch, "")
    DELETE = partial(r.delete, "")
    HEAD = partial(r.head, "")
    OPTIONS = partial(r.options, "")
    TRACE = partial(r.trace, "")


class PathValidationError(Exception):
    """A problem relating to an HTTP path configuration."""


@dataclass(init=False)
class HTTPPathComponent:
    """
    Represents a component of an HTTP path..

    For example, in the startlette style path specification "/items/{item_id}":

    * items is a part where is_constant is true
    * item_id is a part where is_constant is false
    * item_id, implicitely or explicitely has trailing_slash set to False.

    Args:
        value (str): the path component value.
        trailing_slash (bool | EllipsisType, optional): Whether to render a trailing slash
            when it is the last component of a path. The default value, ..., is a
            sentinel to indicate it should be left to the caller to decide whether to
            render a trailing slash.


    Raises:
        PathValidationError: Path doesn't match relevent regex.

    """

    PATH_ALLOWED_REGEX = re.compile(r"^[0-9A-Za-z\-_]*$|^{[0-9A-Za-z\-_]*}$")
    PATH_CONSTANT_REGEX = re.compile(r"^[0-9A-Za-z\-_]*$")
    value: str
    is_constant: bool
    trailing_slash: bool | EllipsisType

    def __init__(self, value: str, /, trailing_slash: bool | EllipsisType = ...):
        if not self.PATH_ALLOWED_REGEX.match(value):
            raise PathValidationError(
                f"HTTP path {value=} is invalid; does not patch pattern {self.PATH_ALLOWED_REGEX.pattern}"
            )
        self.is_constant = bool(self.PATH_CONSTANT_REGEX.match(value))
        self.value = value
        self.trailing_slash = trailing_slash

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(value={self.value}, trailing_slash={self.trailing_slash})"

    def __str__(self) -> str:
        return self.value


class TrailingSlashPolicy:
    """
    Defines how to decide on whether to use a trailing slash.

    This is read only where no explicit value has been provided.
    """

    def __init__(self, /, *, on_constant: bool, on_variable: bool):
        self.on_constant = on_constant
        self.on_variable = on_variable

    def __call__(self, path: HTTPPath | HTTPPathComponent) -> bool:
        """Evaluate the policy for the given path or component."""
        if isinstance(path, HTTPPath):
            path = path.parts[-1]
        return self.on_constant if path.is_constant else self.on_variable

    @classmethod
    def default(cls):
        """Provide a default version of this policy."""
        return cls(on_constant=True, on_variable=False)


class HTTPPath:
    """Represents an HTTP path made up of a tuple of HTTP path components."""

    def __init__(
        self,
        path: str | tuple[HTTPPathComponent, ...],
        /,
        router: APIRouter,
        trailing_slash_policy: TrailingSlashPolicy,
        annotation_pipeline: AnnotatedFunctionAdaptorPipeline,
    ):
        self.router = router
        self.path = path
        self.parts = self._path_parts()
        self.trailing_slash_policy = trailing_slash_policy
        decorator = partial(
            EndpointDecorator, path=self, annotation_pipeline=annotation_pipeline
        )
        if TYPE_CHECKING:
            self.GET = GET
            self.POST = POST
            self.PUT = PUT
            self.PATCH = PATCH
            self.DELETE = DELETE
            self.OPTIONS = OPTIONS
            self.HEAD = HEAD
            self.TRACE = TRACE
        else:
            self.GET = decorator(HTTPMethod.GET)
            self.POST = decorator(HTTPMethod.POST)
            self.PUT = decorator(HTTPMethod.PUT)
            self.PATCH = decorator(HTTPMethod.PATCH)
            self.DELETE = decorator(HTTPMethod.DELETE)
            self.OPTIONS = decorator(HTTPMethod.OPTIONS)
            self.HEAD = decorator(HTTPMethod.HEAD)
            self.TRACE = decorator(HTTPMethod.TRACE)
        self.DEPENDS = DependencyDecorator(router=router, path=self)

    def _path_parts(self) -> tuple[HTTPPathComponent, ...]:
        if isinstance(self.path, str):
            if self.path:
                self.trailing_slash = self.path[-1] == "/"
            else:
                self.trailing_slash = True
            result_parts: list[HTTPPathComponent] = []
            parts = self.path.split("/")
        else:
            self.trailing_slash = bool(self.path[-1])
            result_parts = list(self.path)
            parts = []
        for index, part in enumerate(parts):
            if index == len(parts) - 1:
                trailing_slash = self.trailing_slash
            else:
                trailing_slash = ...
            result_parts.append(HTTPPathComponent(part, trailing_slash=trailing_slash))
        return tuple(result_parts)

    def __str__(self):
        if not self.path:
            return "/"
        retval = "/".join(part.value for part in self.parts if part.value)
        if not retval:
            retval = "/"
        if retval[0] != "/":
            retval = "/" + retval
        if (
            self.parts[-1].trailing_slash is True
            or self.parts[-1].trailing_slash is ...
            and self.trailing_slash_policy(self)
        ) and retval[-1] != "/":
            retval = retval + "/"
        return retval

    def __call__(
        self, value: str, /, *, trailing_slash: bool | EllipsisType = ...
    ) -> HTTPPath:
        """Provide a child HTTP path."""
        return HTTPPath(
            tuple(
                self.parts + (HTTPPathComponent(value, trailing_slash=trailing_slash),)
            ),
            trailing_slash_policy=self.trailing_slash_policy,
            router=self.router,
            annotation_pipeline=(),
        )


@dataclass
class DeferredDecoratorCall:
    """Represents a call made whose outcome is deferred from class definition to class instantiation."""

    path: DeferredHTTPPath
    method: HTTPMethod | Literal["DEPENDS"]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


class DeferredHTTPPath:
    """
    Construct the parameters of a futute existing HTTP path.

    This serves the role of the HTTPPath object when defining
    class-based viewsets. It captures and records the parameters
    that are used on it, which can be used to construct the corresponding
    HTTPPath when the viewset class is instantiated.
    """

    METADATA_KEY = "_deferred_decorations"

    def __init__(self, path: str = "", **kwargs: Any) -> None:
        self.path = path
        self.kwargs = kwargs
        if TYPE_CHECKING:
            self.GET = GET
            self.POST = POST
            self.PUT = PUT
            self.PATCH = PATCH
            self.DELETE = DELETE
            self.OPTIONS = OPTIONS
            self.HEAD = HEAD
            self.TRACE = TRACE
        else:
            self.GET = self._decorator_factory(HTTPMethod.GET)
            self.POST = self._decorator_factory(HTTPMethod.POST)
            self.PUT = self._decorator_factory(HTTPMethod.PUT)
            self.PATCH = self._decorator_factory(HTTPMethod.PATCH)
            self.DELETE = self._decorator_factory(HTTPMethod.DELETE)
            self.OPTIONS = self._decorator_factory(HTTPMethod.OPTIONS)
            self.HEAD = self._decorator_factory(HTTPMethod.HEAD)
            self.TRACE = self._decorator_factory(HTTPMethod.TRACE)
            self.DEPENDS = self._decorator_factory("DEPENDS")

    if TYPE_CHECKING:
        # Fake DEPENDS for the type-checker to not baulk over
        # since it doesn't have a chance to understand otherwise.
        def DEPENDS(self):
            """
            Register a dependency function.

            This is a function that will run for all endpoints
            on this path or any child paths.
            """

            def _inner(func: Callable[..., Any]) -> Callable[..., Any]:
                return func

            return _inner

    def _decorator_factory(self, method: HTTPMethod | Literal["DEPENDS"]):
        def _middle(*args: Any, **kwargs: Any):
            def _inner(func: Callable[..., Any]) -> Callable[..., Any]:
                if not hasattr(func, self.METADATA_KEY):
                    setattr(func, self.METADATA_KEY, [])
                metadata: list[DeferredDecoratorCall] = getattr(func, self.METADATA_KEY)
                metadata.append(
                    DeferredDecoratorCall(
                        path=self, method=method, args=args, kwargs=kwargs
                    )
                )
                return func

            return _inner

        return _middle

    def __call__(self, value: str, /, **kwargs: Any):
        """Access a child deferred http path."""
        return DeferredHTTPPath(self.path + "/" + value, **kwargs)

    def apply(self, viewset: ViewSet, call: DeferredDecoratorCall):
        """Convert to an HTTPPath in the context of a given viewset."""
        return HTTPPath(
            str(viewset.root_path) + call.path.path,
            viewset.router,
            viewset.trailing_slash_policy,
            viewset.annotation_adaptors,
        )


self = DeferredHTTPPath()
