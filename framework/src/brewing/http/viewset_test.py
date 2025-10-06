"""Unit tests for the viewset class."""

from brewing.http import ViewSet
from fastapi import APIRouter


def test_viewset_router_if_not_provided():
    """A router is created if it was not provided."""
    assert isinstance(ViewSet().router, APIRouter)


def test_viewset_router_if_provided():
    """If a router was provided, it is used."""
    router = APIRouter()
    assert ViewSet(router=router).router is router
