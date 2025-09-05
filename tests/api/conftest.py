import pytest
from fastapi import FastAPI
from pytest_subtests import SubTests

from tests.api.scenario import UserTestScenario


@pytest.fixture
def scenario(subtests: SubTests, app: FastAPI) -> UserTestScenario:
    return UserTestScenario(subtests=subtests, app=app)
