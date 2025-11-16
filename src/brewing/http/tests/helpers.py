from typing import Annotated

from fastapi import Header
from pydantic import BaseModel


class SomeData(BaseModel):
    """Basic response data structure."""

    something: list[int]
    data: str | None


def dependency(data: Annotated[str | None, Header()] = None):
    """Test dependency that parses from an HTTP header."""
    return data
