# Cauldron

Cauldron is a python application framework  built to combine and enhance the best in breed packages in the python ecosystem.

## The pitch

```python
from cauldron_incubator import Application, BaseConfiguration, build_cli
from cauldron_incubator.http import ViewSet, collection
from cauldron_incubator.testing import TestClient


class HelloCauldron(ViewSet):

    base_path = ("hello",)

    @collection.GET()
    def greet(self, whom:str="cauldron")->str:
        return f"hello, {whom}!"


class Configuration(BaseConfiguration):
    title = "Project Manager Service"
    description = "Maintains Filesystem Projects over time"
    version = "0.0.1"
    cli_provider = build_cli


application = Application[Configuration](viewsets=[HelloCauldron()])

testclient = TestClient(application.app)
result = testclient.get("/hello/?whom=eric")
assert result.status_code == 200
assert "hello, eric!" in result.text

```

## Installation

Use your preferred python package manager to install cauldron. The author strongly recommends [uv](https://docs.astral.sh/uv/).

```
uv add cauldron
```
