"""Test use of the first parameter.

Handling this paramater is the basis of class based views
but also can be used for functional views.
"""

from dataclasses import dataclass, field

from brewing.http import ViewSet, status
from brewing.http.testing import new_client


@dataclass
class CluckingViewSet(ViewSet):
    sound: str = field(kw_only=True)


def test_untyped_first_parameter():
    vs1 = CluckingViewSet(sound="cluck")

    @vs1.GET()
    def make_sound(self, *, shout: bool = False) -> str:  # type: ignore
        assert isinstance(self, CluckingViewSet)
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


def test_viewset_typed_first_parameter():
    vs1 = CluckingViewSet(sound="cluck")

    @vs1.GET()
    def make_sound(self: CluckingViewSet, *, shout: bool = False) -> str:  # type: ignore
        sound = self.sound
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
