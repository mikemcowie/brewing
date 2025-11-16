"""Unit tests for the viewset class."""

from fastapi import APIRouter

from brewing.http import ViewSet, ViewsetOptions


def new_vs():
    """Return an empty viewset."""
    return ViewSet(ViewsetOptions())


def test_viewset_router_if_not_provided():
    """A router is created if it was not provided."""
    assert isinstance(ViewSet(ViewsetOptions()).router, APIRouter)


def test_viewset_router_if_provided():
    """If a router was provided, it is used."""
    router = APIRouter()
    assert ViewSet(ViewsetOptions(), router=router).router is router
