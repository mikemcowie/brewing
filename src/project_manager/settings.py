from typing import TYPE_CHECKING, Any

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    if TYPE_CHECKING:

        def __init__(*_: Any, **__: Any) -> None:
            pass

    model_config = SettingsConfigDict(frozen=True)
    PGHOST: str
    PGPORT: int
    PGDATABASE: str
    PGUSER: str
    PGPASSWORD: SecretStr
    SECRET_KEY: SecretStr


def settings() -> Settings:
    return Settings()
