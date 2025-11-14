"""CLI entrypoint for brewing."""

from brewing.main import main_cli

cli = main_cli()

if __name__ == "__main__":
    cli()
