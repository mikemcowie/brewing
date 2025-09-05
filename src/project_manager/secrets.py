from pydantic import SecretStr


def secret_value(value: str | SecretStr) -> str:
    if isinstance(value, str):
        return value
    return value.get_secret_value()
