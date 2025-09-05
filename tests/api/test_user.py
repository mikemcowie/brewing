from __future__ import annotations

from fastapi import status

from tests.api.scenario import Expectations, UserTestScenario


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
