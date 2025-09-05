from pathlib import Path
from unittest.mock import patch

from project_manager.app import cli
from project_manager.migrations import versions
from typer.testing import CliRunner


def test_run_cli() -> None:
    with patch("cauldron.cli.uvicorn.run") as uvicorn_run:
        result = CliRunner().invoke(cli, ["api", "--workers", "2"])
        assert result.exit_code == 0, result.stderr + result.stdout
        uvicorn_run.assert_called_once_with(
            "project_manager.app:api", workers=2, factory=True
        )


def test_run_dev_cli() -> None:
    with patch("cauldron.cli.uvicorn.run") as uvicorn_run:
        result = CliRunner().invoke(cli, ["dev", "api"])
        assert result.exit_code == 0, result.stderr + result.stdout
        uvicorn_run.assert_called_once_with(
            "project_manager.app:dev_api", reload=True, factory=True
        )


def test_db_upgrade_downgrade(postgresql: None) -> None:
    result = CliRunner().invoke(cli, ["db", "upgrade"])
    assert result.exit_code == 0, result.stderr + result.stdout
    result = CliRunner().invoke(cli, ["db", "downgrade", "--revision", "base"])
    assert result.exit_code == 0, result.stderr + result.stdout
    result = CliRunner().invoke(cli, ["db", "stamp", "--revision", "head"])
    assert result.exit_code == 0, result.stderr + result.stdout
    result = CliRunner().invoke(cli, ["db", "stamp", "--revision", "base"])
    assert result.exit_code == 0, result.stderr + result.stdout
    result = CliRunner().invoke(cli, ["dev", "db", "upgrade"])
    assert result.exit_code == 0, result.stderr + result.stdout
    result = CliRunner().invoke(cli, ["dev", "db", "downgrade", "--revision", "base"])
    assert result.exit_code == 0, result.stderr + result.stdout
    result = CliRunner().invoke(cli, ["dev", "db", "stamp", "--revision", "head"])
    assert result.exit_code == 0, result.stderr + result.stdout
    result = CliRunner().invoke(cli, ["dev", "db", "stamp", "--revision", "base"])
    assert result.exit_code == 0, result.stderr + result.stdout


def test_create_revision(postgresql: None) -> None:
    initial_revisions = sorted(Path(versions.__file__).parent.glob("*.py"))
    result = CliRunner().invoke(
        cli, ["dev", "db", "revision", "--message", "test revision"]
    )
    assert result.exit_code == 0, result.stderr + result.stdout
    final_revisons = sorted(Path(versions.__file__).parent.glob("*.py"))
    assert len(final_revisons) == len(initial_revisions) + 1
    extra = set(final_revisons) - set(initial_revisions)
    for e in extra:
        e.unlink()
