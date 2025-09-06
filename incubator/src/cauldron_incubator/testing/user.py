from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import SecretStr

from cauldron_incubator.http import CauldronHTTP, status
from cauldron_incubator.testing.scenario import Expectations, TestScenario, User

if TYPE_CHECKING:
    from httpx import Response
    from pytest_subtests import SubTests


class UserTestScenario:
    def __init__(self, subtests: SubTests, app: CauldronHTTP):
        self.scenario = TestScenario(subtests=subtests, app=app)
        self.subtests = self.scenario.subtests
        self.user1, self.user2, self.bad_guy = (
            self.scenario.user1,
            self.scenario.user2,
            self.scenario.bad_guy,
        )
        self.validate_expectations = self.scenario.validate_expectations

    def register(self, user: User, test_name: str, expectations: Expectations) -> None:
        with self.subtests.test(test_name):
            self.validate_expectations(
                expectations,
                user.client.post(
                    "/users/register",
                    json=user.register.model_dump(mode="json")
                    | {"password": user.register.password.get_secret_value()},
                ),
            )

    def register_all_users(self) -> None:
        for user in self.user1, self.user2, self.bad_guy:
            self.register(
                user=user,
                test_name=f"register-user-{user.register.email}",
                expectations=Expectations(status=status.HTTP_201_CREATED),
            )

    def login_all_users(self) -> None:
        for user in self.user1, self.user2, self.bad_guy:
            self.login(
                user=user,
                test_name=f"login-user-{user.register.email}",
                expectations=Expectations(),
            )

    def login(self, user: User, test_name: str, expectations: Expectations) -> None:
        with self.subtests.test(test_name):
            payload = user.login.model_dump(mode="json") | {
                "password": user.login.password.get_secret_value()
            }
            result = self.validate_expectations(
                expectations,
                user.client.post("/users/login", data=payload),
            )
            if result.status_code == status.HTTP_200_OK:
                user.client.headers["authorization"] = (
                    f"Bearer {result.json()['access_token']}"
                )

    def retrieve_profile(
        self, user: User, test_name: str, expectations: Expectations
    ) -> Response:
        result = user.client.get("/users/profile")
        with self.subtests.test(test_name):
            self.validate_expectations(expectations, result)
        return result


class BaseTestUser:
    @pytest.fixture
    def scenario(self, subtests: SubTests, app: CauldronHTTP) -> UserTestScenario:
        return UserTestScenario(subtests=subtests, app=app)

    def test_retrieve_profile_with_no_registered_user(
        self, scenario: UserTestScenario
    ) -> None:
        scenario.retrieve_profile(
            scenario.user1,
            "expect-fail-if-not-logged-in",
            Expectations(
                status=status.HTTP_401_UNAUTHORIZED,
                json={"detail": "unauthorized"},
            ),
        )

    def test_login_without_registering(self, scenario: UserTestScenario) -> None:
        scenario.login(
            scenario.user1,
            "login-witout-having-registered",
            Expectations(
                status=status.HTTP_401_UNAUTHORIZED,
                json={"detail": "incorrect username or password"},
            ),
        )

    def test_register_login_and_profile(self, scenario: UserTestScenario) -> None:
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

    def test_login_with_wrong_password(self, scenario: UserTestScenario) -> None:
        scenario.register(
            scenario.user1, "register", Expectations(status=status.HTTP_201_CREATED)
        )
        scenario.user1.login.password = SecretStr("WRONG-PASSWORD")
        scenario.login(
            scenario.user1,
            test_name="wrong-password",
            expectations=Expectations(
                status=status.HTTP_401_UNAUTHORIZED,
                json={"detail": "incorrect username or password"},
            ),
        )
