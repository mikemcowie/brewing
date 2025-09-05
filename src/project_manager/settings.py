from typing import TYPE_CHECKING

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    if TYPE_CHECKING:

        def __init__(*_, **__):
            pass

    model_config = SettingsConfigDict(frozen=True)
    PGHOST: str
    PGPORT: int
    PGDATABASE: str
    PGUSER: str
    PGPASSWORD: SecretStr
    SECRET_KEY: SecretStr


def settings():
    return Settings()
