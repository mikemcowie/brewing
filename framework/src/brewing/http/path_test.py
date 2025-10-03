"""Unit tests for HTTP path."""

import pytest
from .path import HTTPPathComponent, PathValidationError, HTTPPath


@pytest.mark.parametrize(
    ("reason", "value", "expected_error", "is_constant"),
    (
        ("happy-path-constant", "foo", None, True),
        ("happy-path-variable", "{foo_id}", None, False),
        ("invalid-char", "foo?", PathValidationError, None),
        ("slash-disallowd", "foo/bar", PathValidationError, None),
    ),
)
def test_http_path_components(
    reason: str,
    value: str,
    expected_error: type[Exception] | None,
    is_constant: bool | None,
):
    """Validate scenarios about http path compoments."""
    try:
        path_component = HTTPPathComponent(value)
    except Exception as error:
        if expected_error and isinstance(error, expected_error):
            return
        else:
            raise
    assert path_component.is_constant == is_constant


def test_root_path():
    path = HTTPPath("")
    assert path.parts[-1].trailing_slash
    assert str(path) == "/"


def test_http_path_constant_one_part_trailing_slash():
    path = HTTPPath("/foo/")
    assert path.parts[-1].trailing_slash
    assert str(path) == "/foo/"


def test_http_path_constant_one_no_trailing_slash():
    path = HTTPPath("foo")
    assert not path.parts[-1].trailing_slash
    assert str(path) == "/foo"


def test_http_path_one_part_variable_trailing_slash():
    path = HTTPPath("/{foo_id}/")
    assert path.parts[-1].trailing_slash
    assert str(path) == "/{foo_id}/"


def test_http_path_one_part_variable_no_trailing_slash():
    path = HTTPPath("{foo_id}")
    assert not path.parts[-1].trailing_slash
    assert str(path) == "/{foo_id}"
