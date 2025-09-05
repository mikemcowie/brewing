from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresqlSettings(BaseSettings):
    if TYPE_CHECKING:

        def __init__(*_: Any, **__: Any) -> None:
            pass

    model_config = SettingsConfigDict(frozen=True)
    SECRET_KEY: SecretStr = Field(default=..., min_length=32)
