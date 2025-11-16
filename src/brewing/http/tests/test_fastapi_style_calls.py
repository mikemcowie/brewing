"""Viewset can be used as a proxy for fastapi APIRouter."""

from http import HTTPMethod
from typing import Annotated

import pytest
from fastapi import Depends, Query

from brewing.http import ViewSet, ViewsetOptions, status
from brewing.http.endpoint_decorator import EndpointDecorator
from brewing.http.testing import new_client

from .helpers import SomeData, dependency

vs1 = ViewSet(ViewsetOptions())


@pytest.mark.parametrize("method", HTTPMethod)
def test_method_for_each_http_method_mapped_to_router(method: HTTPMethod):
    """Validate consistent structure of the decorators."""
    if method is HTTPMethod.CONNECT:
        pytest.skip("not supported")
        return
    fastapi_compat_decorator = getattr(vs1, method.value.lower())
    brewing_native_decorator = getattr(vs1, method.value.upper())
    assert fastapi_compat_decorator == getattr(vs1.router, method.value.lower())
    assert isinstance(brewing_native_decorator, EndpointDecorator)
    assert brewing_native_decorator.wraps == fastapi_compat_decorator


@vs1.get("/", response_model=SomeData)
def endpoint1(
    data: Annotated[str | None, Depends(dependency)], count: Annotated[int, Query()] = 0
):
    """Return some data."""
    return SomeData(something=list(range(count)), data=data)


def test_functional_fastapi_style_endpoint():
    """Test that the above declared fastapi style endpoint works as per fastapi."""
    client = new_client(vs1)
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["something"] == []
    response = client.get("/?count=2")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["something"] == [0, 1]
    response = client.get("/", headers={"data": "foo"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"] == "foo"
