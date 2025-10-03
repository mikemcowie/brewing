"""Utilities for constructing and validating HTTP paths."""

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


class HTTPPath:
    """Represents an HTTP path made up of a tuple of HTTP path components."""

    def __init__(self, path: str, /):
        if path:
            self.trailing_slash = path[-1] == "/"
        else:
            self.trailing_slash = True
        parts = path.split("/")
        self._parts: list[HTTPPathComponent] = []
        for index, part in enumerate(parts):
            if index == len(parts) - 1:
                trailing_slash = self.trailing_slash
            else:
                trailing_slash = ...
            self._parts.append(HTTPPathComponent(part, trailing_slash=trailing_slash))

    @cached_property
    def parts(self):
        """The HTTP paath components."""
        return tuple(self._parts)

    def __str__(self):
        retval = "/".join(str(part) for part in self.parts) or "/"
        if retval[0] != "/":
            retval = "/" + retval
        return retval
