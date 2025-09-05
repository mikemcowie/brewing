from fastapi import status


class DomainError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "generic error"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.detail

    def __str__(self):
        return ": ".join((str(self.status_code), self.detail))


class NotFound(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "resource not found"


class Unauthorized(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "unauthorized"
