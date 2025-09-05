from typing import Annotated

import typer
import uvicorn

cli = typer.Typer(add_help_option=True, no_args_is_help=True)
dev = typer.Typer(add_help_option=True, no_args_is_help=True)
cli.add_typer(dev, name="dev")


API = "project_manager.api:api"


@cli.command(name="api")
async def api(workers: Annotated[int, typer.Option(envvar="API_WORKERS")]):
    """Run api"""

    uvicorn.run("project_manager.api:api", workers=workers)


@dev.command("api")
async def dev_api():
    """Run development api woth hot reload."""

    uvicorn.run("project_manager.api:api", reload=True)
