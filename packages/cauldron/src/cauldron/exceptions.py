from __future__ import annotations

from fastapi import status


class DomainError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "generic error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.detail


class NotFound(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "resource not found"


class Unauthorized(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "unauthorized"


class Forbidden(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "forbidden"
