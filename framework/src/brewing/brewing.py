from typing import Any, Callable, Annotated, NamedTuple
from typer import Option
from brewing.cli import CLI, CLIOptions
from brewing.http import BrewingHTTP
import uvicorn


class BrewingCLIOptions(NamedTuple):
    name: str


class Brewing:
    def __init__(self, name: str, **components: Any):
        self.cli = CLI(CLIOptions(name=name))
        self.typer = self.cli.typer
        handlers: dict[type, Callable[[tuple[str, Any]], Any]] = {
            BrewingHTTP: self.init_http_component
        }
        self.components = components
        for name, component in components.items():
            handlers[type(component)]((name, component))

    def __getattr__(self, name: str):
        try:
            return self.components[name]
        except KeyError as error:
            raise AttributeError(f"no attribute '{name}' in object {self}.") from error

    def init_http_component(self, component: tuple[str, BrewingHTTP]):
        name, http = component

        @self.cli.typer.command(name)
        def run(
            reload: Annotated[bool, Option()],
            workers: None | int = None,
            host: str = "0.0.0.0",
            port: int = 8000,
        ):
            uvicorn.run(
                http.app_string_identifier,
                host=host,
                workers=workers,
                port=port,
                reload=reload,
            )
