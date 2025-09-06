from brewing_incubator.exceptions import DomainError
from brewing_incubator.http import status


class LoginFailure(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "incorrect username or password"


class InvalidToken(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "invalid token."
