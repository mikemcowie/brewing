from __future__ import annotations

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import yaml  # type:ignore[import-untyped]
from testcontainers.postgres import PostgresContainer  # type:ignore[import-untyped]

from cauldron.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Generator

logger = get_logger()


class DevelopmentEnvironment:
    COMPOSE_FILE = Path(__file__).parent / "compose.yaml"

    def run(self) -> None:  # pragma: no cover
        logger.info("setting up dev environment")
        compose_data = yaml.load(self.COMPOSE_FILE.read_text(), yaml.SafeLoader)
        os.environ["PGPASSWORD"] = compose_data["services"]["db"]["environment"][
            "POSTGRES_PASSWORD"
        ]
        os.environ["PGDATABASE"] = compose_data["services"]["db"]["environment"][
            "POSTGRES_DB"
        ]
        os.environ["PGUSER"] = compose_data["services"]["db"]["environment"][
            "POSTGRES_USER"
        ]
        os.environ["PGHOST"] = "127.0.0.1"
        os.environ["PGPORT"] = "5432"
        with ThreadPoolExecutor() as executor:
            executor.submit(self._run_compose)
        logger.info("finished setting up dev environment")

    @contextmanager
    def testcontainer_postgresql(self) -> Generator[None]:
        with PostgresContainer() as pg:
            os.environ["PGPASSWORD"] = pg.password
            os.environ["PGDATABASE"] = pg.dbname
            os.environ["PGUSER"] = pg.username
            os.environ["PGHOST"] = "127.0.0.1"
            os.environ["PGPORT"] = str(pg.get_exposed_port(pg.port))
            yield

    def _run_compose(self) -> None:  # pragma: no cover
        logger.info("running docker compose")
        subprocess.run(
            ["docker", "compose", "up", "-d"], check=False, cwd=self.COMPOSE_FILE.parent
        )
