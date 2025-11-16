"""Unit tests for HTTP path."""

import pytest
from fastapi import APIRouter

from .path import HTTPPath, HTTPPathComponent, PathValidationError, TrailingSlashPolicy

router = APIRouter()


@pytest.mark.parametrize(
    ("reason", "value", "expected_error", "is_constant"),
    [
        ("happy-path-constant", "foo", None, True),
        ("happy-path-variable", "{foo_id}", None, False),
        ("invalid-char", "foo?", PathValidationError, None),
        ("slash-disallowd", "foo/bar", PathValidationError, None),
    ],
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
    path = HTTPPath(
        "",
        trailing_slash_policy=TrailingSlashPolicy.default(),
        router=router,
        annotation_pipeline=(),
    )
    assert path.parts[-1].trailing_slash
    assert str(path) == "/"


def test_http_path_constant_one_part_trailing_slash():
    path = HTTPPath(
        "/foo/",
        trailing_slash_policy=TrailingSlashPolicy.default(),
        router=router,
        annotation_pipeline=(),
    )
    assert path.parts[-1].trailing_slash
    assert str(path) == "/foo/"


def test_http_path_constant_one_no_trailing_slash():
    path = HTTPPath(
        "foo",
        trailing_slash_policy=TrailingSlashPolicy.default(),
        router=router,
        annotation_pipeline=(),
    )
    assert not path.parts[-1].trailing_slash
    assert str(path) == "/foo"


def test_http_path_one_part_variable_trailing_slash():
    path = HTTPPath(
        "/{foo_id}/",
        trailing_slash_policy=TrailingSlashPolicy.default(),
        router=router,
        annotation_pipeline=(),
    )
    assert path.parts[-1].trailing_slash
    assert str(path) == "/{foo_id}/"


def test_http_path_one_part_variable_no_trailing_slash():
    path = HTTPPath(
        "{foo_id}",
        trailing_slash_policy=TrailingSlashPolicy.default(),
        router=router,
        annotation_pipeline=(),
    )
    assert not path.parts[-1].trailing_slash
    assert str(path) == "/{foo_id}"


def test_extend_http_path():
    path = HTTPPath(
        "foo/",
        trailing_slash_policy=TrailingSlashPolicy.default(),
        router=router,
        annotation_pipeline=(),
    )
    assert path.parts[-1].trailing_slash
    assert str(path) == "/foo/"
    child1 = path("{foo_id}", trailing_slash=False)
    assert str(child1) == "/foo/{foo_id}"
    child2 = path("{foo_id}", trailing_slash=True)
    assert str(child2) == "/foo/{foo_id}/"
    grandchild_1 = child1("bar", trailing_slash=True)
    assert str(grandchild_1) == "/foo/{foo_id}/bar/"
    grandchild_2 = child2("bar", trailing_slash=True)
    assert str(grandchild_2) == "/foo/{foo_id}/bar/"
    grandchild_3 = child1("bar", trailing_slash=False)
    assert str(grandchild_3) == "/foo/{foo_id}/bar"
    grandchild_4 = child2("bar", trailing_slash=False)
    assert str(grandchild_4) == "/foo/{foo_id}/bar"
