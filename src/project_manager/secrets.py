from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import SecretStr


def secret_value(value: str | SecretStr) -> str:
    if isinstance(value, str):
        return value
    return value.get_secret_value()
