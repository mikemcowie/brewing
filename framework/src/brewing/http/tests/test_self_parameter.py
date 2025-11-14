"""Test use of the first parameter.

Handling this paramater is the basis of class based views
but also can be used for functional views.
"""

from dataclasses import dataclass, field
from ..testing import new_client

from brewing.http import ViewSet, status, ViewsetOptions


## Setup - we'll construct a subclass of viewset.
# we won't have any class-based endpoints, but
# the subclass will have a couple of extra attributes.
# the first parameter of a functional endpoint, if untyped
# or typed as the tyype of the ViewSet, will be adapted via fastapi depends mechanism
# to be passed.
@dataclass
class CluckingViewsetOptions(ViewsetOptions):
    sound: str = field(kw_only=True)


class CluckingViewSet(ViewSet[CluckingViewsetOptions]):
    pass


def test_untyped_first_parameter():
    vs1 = CluckingViewSet(CluckingViewsetOptions(sound="cluck"))

    @vs1.GET()
    def make_sound(self, *, shout: bool = False) -> str:  # type: ignore
        assert isinstance(self, CluckingViewSet)
        sound: str = self.viewset_options.sound
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
    vs1 = CluckingViewSet(CluckingViewsetOptions(sound="cluck"))

    @vs1.GET()
    def make_sound(self: CluckingViewSet, *, shout: bool = False) -> str:  # type: ignore
        sound = self.viewset_options.sound
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
