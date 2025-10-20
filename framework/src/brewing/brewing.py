from typing import Any
from brewing.cli import CLI


class Brewing:
    def __init__(self, name: str, *components: Any):
        self.cli = CLI(name)
        self.typer = self.cli.typer
