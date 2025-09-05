# Cauldron

Cauldron is a python application framework  built to combine and enhance the best in breed packages in the python ecosystem.

## The pitch

```python
from cauldron import Application, ViewSet, collection
from cauldron.testing import TestClient


class HelloCauldron(ViewSet):

    @collection.GET()
    def greet(self, whom:str="cauldron")->str:
        return f"hello, {whom}!"


application = Application(viewsets=[HelloCauldron()])

testclient = TestClient(application)
result = testclient.get("?whom=eric")
assert result.status_code == 200
assert result.stdout == "hello, eric!"


```

## Installation

Use your preferred python package manager to install cauldron. The author strongly recommends [uv](https://docs.astral.sh/uv/).

```
uv add cauldron
```
