"""Utilities for constructing and validating HTTP paths."""

from __future__ import annotations
from dataclasses import dataclass
import re
from types import EllipsisType
from functools import cached_property


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
        trailing_slash_policy: TrailingSlashPolicy,
    ):
        self.trailing_slash_policy = trailing_slash_policy
        self.path = path
        if isinstance(path, str):
            if path:
                self.trailing_slash = path[-1] == "/"
            else:
                self.trailing_slash = True
            self._parts: list[HTTPPathComponent] = []
            parts = path.split("/")
        else:
            self.trailing_slash = bool(path[-1])
            self._parts = list(path)
            parts = []
        for index, part in enumerate(parts):
            # if not part:
            #    continue
            if index == len(parts) - 1:
                trailing_slash = self.trailing_slash
            else:
                trailing_slash = ...
            self._parts.append(HTTPPathComponent(part, trailing_slash=trailing_slash))

    @cached_property
    def parts(self) -> tuple[HTTPPathComponent, ...]:
        """The HTTP paath components."""
        return tuple(self._parts)

    def __str__(self):
        if not self.path:
            return "/"
        retval = "/".join(part.value for part in self.parts if part.value)
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
        )
