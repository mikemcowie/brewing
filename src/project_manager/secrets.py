from pydantic import SecretStr


def secret_value(value: str | SecretStr):
    if isinstance(value, str):
        return value
    return value.get_secret_value()
