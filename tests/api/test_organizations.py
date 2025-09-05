from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from fastapi import FastAPI, status
from polyfactory.factories.pydantic_factory import ModelFactory

from project_manager.organizations.models import Organization
from tests.api.scenario import Expectations, User
from tests.api.test_user import UserTestScenario

if TYPE_CHECKING:
    from httpx import Response
    from pytest_subtests import SubTests


class OrganizationTestScenario(UserTestScenario):
    def list_organizations(self, user: User, expectations: Expectations) -> Response:
        result = user.client.get("/organizations/")
        self.validate_expectations(expectations, result)
        return result

    def create_organization(
        self, user: User, organization: dict[str, Any], expectations: Expectations
    ) -> Response:
        result = user.client.post("/organizations/", json=organization)
        self.validate_expectations(expectations, result)
        return result

    def update_organization(
        self,
        user: User,
        organization_id: str,
        organization: dict[str, Any],
        expectations: Expectations,
    ) -> Response:
        result = user.client.put(f"/organizations/{organization_id}", json=organization)
        self.validate_expectations(expectations, result)
        return result

    def read_organization(
        self, user: User, organization_id: str, expectations: Expectations
    ) -> Response:
        result = user.client.get(f"/organizations/{organization_id}")
        self.validate_expectations(expectations, result)
        return result

    def delete_organization(
        self, user: User, organization_id: str, expectations: Expectations
    ) -> Response:
        result = user.client.delete(f"/organizations/{organization_id}")
        self.validate_expectations(expectations, result)
        return result


@pytest.fixture
def scenario(subtests: SubTests, app: FastAPI) -> OrganizationTestScenario:
    return OrganizationTestScenario(subtests=subtests, app=app)


def test_organization_crud(
    app: FastAPI, subtests: SubTests, scenario: OrganizationTestScenario
) -> None:
    scenario.register_all_users()
    scenario.login_all_users()

    factory = ModelFactory.create_factory(Organization.schemas().create)
    update_factory = ModelFactory.create_factory(Organization.schemas().update)
    new_org = factory.build()
    with subtests.test("list-before"):
        result = scenario.list_organizations(
            user=scenario.user1, expectations=Expectations(status=status.HTTP_200_OK)
        )
        assert len(result.json()) == 0

    with subtests.test("create-organization"):
        create_result = scenario.create_organization(
            scenario.user1,
            organization=new_org.model_dump(mode="json"),
            expectations=Expectations(
                status=status.HTTP_201_CREATED, json=new_org.model_dump(mode="json")
            ),
        )
        org_id = create_result.json()["id"]
        with subtests.test("list-after-create"):
            result = scenario.list_organizations(
                user=scenario.user1,
                expectations=Expectations(status=status.HTTP_200_OK),
            )
            assert len(result.json()) == 1
            assert result.json()[0]["id"] == org_id
        with subtests.test("retrieve_after_create"):
            scenario.read_organization(
                scenario.user1,
                organization_id=org_id,
                expectations=Expectations(
                    status=status.HTTP_200_OK,
                    json=create_result.json() | {"id": org_id},
                ),
            )
        update = update_factory.build()
        with subtests.test("update"):
            update_result = scenario.update_organization(
                user=scenario.user1,
                organization_id=org_id,
                organization=update.model_dump(mode="json"),
                expectations=Expectations(
                    status=status.HTTP_200_OK,
                    json=update.model_dump(mode="json") | {"id": org_id},
                ),
            )
            with subtests.test("retrieve_after_update"):
                scenario.read_organization(
                    scenario.user1,
                    organization_id=org_id,
                    expectations=Expectations(
                        status=status.HTTP_200_OK, json=update_result.json()
                    ),
                )
        with subtests.test("delete"):
            scenario.delete_organization(
                scenario.user1,
                organization_id=org_id,
                expectations=Expectations(status=status.HTTP_204_NO_CONTENT),
            )
            with subtests.test("list-after-delete"):
                result = scenario.list_organizations(
                    user=scenario.user1,
                    expectations=Expectations(status=status.HTTP_200_OK),
                )
                assert len(result.json()) == 0
            with subtests.test("retrieve_after_delete"):
                scenario.read_organization(
                    scenario.user1,
                    organization_id=org_id,
                    expectations=Expectations(status=status.HTTP_404_NOT_FOUND),
                )
            with subtests.test("update_after_delete"):
                update_result = scenario.update_organization(
                    user=scenario.user1,
                    organization_id=org_id,
                    organization=update.model_dump(mode="json"),
                    expectations=Expectations(status=status.HTTP_404_NOT_FOUND),
                )
            with subtests.test("delete_after_delete"):
                scenario.delete_organization(
                    scenario.user1,
                    organization_id=org_id,
                    expectations=Expectations(status=status.HTTP_404_NOT_FOUND),
                )
