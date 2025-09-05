from typing import Annotated

import typer
import uvicorn

from project_manager.api import api_factory

cli = typer.Typer(add_help_option=True, no_args_is_help=True)
dev = typer.Typer(add_help_option=True, no_args_is_help=True)
cli.add_typer(dev, name="dev")


@cli.command(name="api")
def api(workers: Annotated[int, typer.Option(envvar="API_WORKERS")]):
    """Run api"""

    uvicorn.run(f"{api_factory.__module__}:{api_factory.__name__}", workers=workers)


@dev.command("api")
def dev_api():
    """Run development api woth hot reload."""

    uvicorn.run(f"{api_factory.__module__}:{api_factory.__name__}", reload=True)
