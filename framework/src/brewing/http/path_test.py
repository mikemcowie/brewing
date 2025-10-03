"""Unit tests for HTTP path."""

import pytest
from .path import HTTPPathComponent, PathValidationError


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
