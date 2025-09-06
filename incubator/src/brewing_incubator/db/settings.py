from typing import TYPE_CHECKING, Any, Protocol

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DBSettingsType(Protocol):
    """Protocol required for the DB settings class."""

    def __init__(*_: Any, **__: Any) -> None: ...
    def uri(self) -> str: ...


class PostgresqlSettings(BaseSettings):
    if TYPE_CHECKING:

        def __init__(*_: Any, **__: Any) -> None:
            pass

    model_config = SettingsConfigDict(frozen=True)
    PGHOST: str
    PGPORT: int
    PGDATABASE: str
    PGUSER: str
    PGPASSWORD: SecretStr

    def uri(self) -> str:
        uri = f"postgresql+psycopg://{self.PGUSER}:{self.PGPASSWORD.get_secret_value()}@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}"
        # raise Exception(uri)
        return uri
