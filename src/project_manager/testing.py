from __future__ import annotations

import os
import random
import string
import subprocess
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

import yaml  # type:ignore[import-untyped]
from testcontainers.postgres import PostgresContainer  # type:ignore[import-untyped]

if TYPE_CHECKING:
    from collections.abc import Generator


@cache
def set_secret_key() -> None:
    os.environ["SECRET_KEY"] = "".join(
        random.choice(string.ascii_letters) for _ in range(32)
    )


@contextmanager
def testcontainer_postgresql() -> Generator[None]:
    with PostgresContainer() as pg:
        os.environ["PGPASSWORD"] = pg.password
        os.environ["PGDATABASE"] = pg.dbname
        os.environ["PGUSER"] = pg.username
        os.environ["PGHOST"] = "127.0.0.1"
        os.environ["PGPORT"] = str(pg.get_exposed_port(pg.port))
        set_secret_key()
        yield


COMPOSE_FILE = Path(__file__).parents[2] / "compose.yaml"


def dev_environment() -> None:
    compose_data = yaml.load(COMPOSE_FILE.read_text(), yaml.SafeLoader)
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
    set_secret_key()
    with ThreadPoolExecutor() as executor:
        executor.submit(run_compose)


def run_compose() -> None:
    subprocess.run(
        ["docker", "compose", "up", "-d"], check=False, cwd=COMPOSE_FILE.parent
    )
