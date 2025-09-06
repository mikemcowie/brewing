from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from faker import Faker
from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import BaseModel, EmailStr, SecretStr

from brewing_incubator.http import BrewingHTTP, status
from brewing_incubator.testing import TestClient

if TYPE_CHECKING:
    from collections.abc import Mapping

    from httpx import Response
    from pytest_subtests import SubTests


@dataclass
class Expectations:
    status: int = status.HTTP_200_OK
    json: Mapping[str, Any] = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)


class UserRegister(BaseModel):
    email: EmailStr
    password: SecretStr


class UserLogin(BaseModel):
    username: EmailStr
    password: SecretStr


class UserLoginFactory(ModelFactory[UserLogin]):
    pass


@dataclass
class User:
    login: UserLogin
    register: UserRegister
    client: TestClient

    @classmethod
    def build(cls, app: BrewingHTTP) -> User:
        login = UserLoginFactory.build()
        login.password = SecretStr(Faker().password(length=15))
        register = UserRegister(email=login.username, password=login.password)
        client = TestClient(app)
        return cls(login, register, client)


class TestScenario:
    __test__ = False

    def __init__(self, subtests: SubTests, app: BrewingHTTP) -> None:
        self.subtests = subtests
        self.user1, self.user2, self.bad_guy = (
            User.build(app=app),
            User.build(app=app),
            User.build(app=app),
        )

    @staticmethod
    def validate_expectations(expectations: Expectations, result: Response) -> Response:
        assert expectations.status == result.status_code, result.content
        if expectations.headers:  # pragma: no cover
            assert expectations.headers.items() <= result.headers.items()
        if expectations.json:
            assert expectations.json.items() <= result.json().items(), (
                expectations.json,
                result.json(),
            )
        return result
