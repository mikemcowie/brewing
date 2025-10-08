"""Test use of the first parameter.

Handling this paramater is the basis of class based views
but also can be used for functional views.
"""

from brewing.http.path import TrailingSlashPolicy
from fastapi import APIRouter
from .helpers import new_client

from brewing.http import ViewSet, status


## Setup - we'll construct a subclass of viewset.
# we won't have any class-based endpoints, but
# the subclass will have a couple of extra attributes.
# the first parameter of a functional endpoint, if untyped
# or typed as the tyype of the ViewSet, will be adapted via fastapi depends mechanism
# to be passed.
class CluckingViewSet(ViewSet):
    def __init__(
        self,
        root_path: str = "",
        router: APIRouter | None = None,
        trailing_slash_policy: TrailingSlashPolicy = TrailingSlashPolicy.default(),
    ):
        super().__init__(root_path, router, trailing_slash_policy)
        self.sound = "cluck"


def test_untyped_first_parameter():
    vs1 = CluckingViewSet()

    @vs1.GET()
    def make_sound(self, *, shout: bool = False) -> str:  # type: ignore
        assert isinstance(self, CluckingViewSet)
        sound: str = self.sound  # type: ignore
        if shout:
            sound = sound.upper()
        return sound

    client = new_client(vs1)
    result = client.get("/")
    assert result.status_code == status.HTTP_200_OK, result.text
    assert result.text == '"cluck"'
    result = client.get("/?shout=1")
    assert result.status_code == status.HTTP_200_OK, result.text
    assert result.text == '"CLUCK"'


def test_viewset_typed_first_parameter():
    vs1 = CluckingViewSet()

    @vs1.GET()
    def make_sound(self: CluckingViewSet, *, shout: bool = False) -> str:  # type: ignore
        sound: str = self.sound
        if shout:
            sound = sound.upper()
        return sound

    client = new_client(vs1)
    result = client.get("/")
    assert result.status_code == status.HTTP_200_OK, result.text
    assert result.text == '"cluck"'
    result = client.get("/?shout=1")
    assert result.status_code == status.HTTP_200_OK, result.text
    assert result.text == '"CLUCK"'
