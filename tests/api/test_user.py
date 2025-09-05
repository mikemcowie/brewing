from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import BaseModel, EmailStr, SecretStr

from project_manager.endpoints import Endpoints

if TYPE_CHECKING:
    from collections.abc import Mapping

    from httpx import Response
    from pytest_subtests import SubTests


class UserLogin(BaseModel):
    username: EmailStr
    password: SecretStr


class UserLoginFactory(ModelFactory[UserLogin]):
    pass


class UserRegister(BaseModel):
    email: EmailStr
    password: SecretStr


@dataclass
class User:
    login: UserLogin
    register: UserRegister
    client: TestClient

    @classmethod
    def build(cls, app: FastAPI) -> User:
        login = UserLoginFactory.build()
        register = UserRegister(email=login.username, password=login.password)
        client = TestClient(app)
        return cls(login, register, client)


@dataclass
class Expectations:
    status: int = status.HTTP_200_OK
    json: Mapping[str, Any] = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)


class UserTestScenario:
    def __init__(self, subtests: SubTests, app: FastAPI) -> None:
        self.subtests = subtests
        self.user1, self.user2, self.bad_guy = (
            User.build(app=app),
            User.build(app=app),
            User.build(app=app),
        )

    @staticmethod
    def validate_expectations(expectations: Expectations, result: Response) -> Response:
        assert expectations.status == result.status_code, result.content
        assert expectations.headers.items() <= result.headers.items()
        assert expectations.json.items() <= result.json().items()
        return result

    def register(self, user: User, test_name: str, expectations: Expectations) -> None:
        with self.subtests.test(test_name):
            self.validate_expectations(
                expectations,
                user.client.post(
                    Endpoints.USERS_REGISTER, json=user.register.model_dump(mode="json")
                ),
            )

    def login(self, user: User, test_name: str, expectations: Expectations) -> None:
        with self.subtests.test(test_name):
            result = self.validate_expectations(
                expectations,
                user.client.post(
                    Endpoints.USERS_LOGIN, data=user.login.model_dump(mode="json")
                ),
            )
            if result.status_code == status.HTTP_200_OK:
                user.client.headers["authorization"] = (
                    f"Bearer {result.json()['access_token']}"
                )

    def retrieve_profile(
        self, user: User, test_name: str, expectations: Expectations
    ) -> None:
        with self.subtests.test(test_name):
            self.validate_expectations(
                expectations, user.client.get(Endpoints.USERS_PROFILE)
            )


@pytest.fixture
def scenario(subtests: SubTests, app: FastAPI) -> UserTestScenario:
    return UserTestScenario(subtests=subtests, app=app)


def test_retrieve_profile_with_no_registered_user(scenario: UserTestScenario) -> None:
    scenario.retrieve_profile(
        scenario.user1,
        "expect-fail-if-not-logged-in",
        Expectations(
            status=status.HTTP_401_UNAUTHORIZED,
            json={"detail": "unauthorized"},
        ),
    )


def test_login_without_registering(scenario: UserTestScenario) -> None:
    scenario.login(
        scenario.user1,
        "login-witout-having-registered",
        Expectations(
            status=status.HTTP_401_UNAUTHORIZED,
            json={"detail": "incorrect username or password"},
        ),
    )


def test_register_login_and_profile(scenario: UserTestScenario) -> None:
    scenario.register(
        scenario.user1, "register", Expectations(status=status.HTTP_201_CREATED)
    )
    scenario.login(scenario.user1, "login", Expectations(status=status.HTTP_200_OK))
    scenario.login(
        scenario.user2,
        "login-user2-fails",
        Expectations(status=status.HTTP_401_UNAUTHORIZED),
    )
    scenario.retrieve_profile(
        scenario.user1,
        test_name="retrieve-profile",
        expectations=Expectations(
            status=status.HTTP_200_OK, json={"email": scenario.user1.login.username}
        ),
    )
