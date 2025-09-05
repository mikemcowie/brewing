from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any

import pytest
from fastapi import FastAPI, status
from polyfactory.factories.pydantic_factory import ModelFactory

from project_manager.organizations.models import Organization
from tests.api.scenario import Expectations, User
from tests.api.test_user import UserTestScenario

if TYPE_CHECKING:
    from httpx import Response
    from polyfactory.factories import BaseFactory
    from pydantic import BaseModel
    from pytest_subtests import SubTests

    from project_manager.resources.models import ReadModelType


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


class TestOrganizationCrud:
    @pytest.fixture(autouse=True)
    def scenario_fixture(
        self, subtests: SubTests, app: FastAPI
    ) -> OrganizationTestScenario:
        self.scenario = OrganizationTestScenario(subtests=subtests, app=app)
        self.subtests = subtests
        self.app = app
        self.bar = None
        self.org_id: str | None = None
        return self.scenario

    @cached_property
    def factory(self) -> type[BaseFactory[BaseModel]]:
        return ModelFactory.create_factory(Organization.schemas().create)

    @cached_property
    def update_factory(self) -> type[BaseFactory[BaseModel]]:
        return ModelFactory.create_factory(Organization.schemas().create)

    @cached_property
    def new_org(self) -> BaseModel:
        return self.factory.build()

    @cached_property
    def updated_org(self) -> BaseModel:
        return self.update_factory.build()

    def pre_create(self) -> None:
        with self.subtests.test("prepare-users"):
            self.scenario.register_all_users()
            self.scenario.login_all_users()
            with self.subtests.test("list-before"):
                result = self.scenario.list_organizations(
                    user=self.scenario.user1,
                    expectations=Expectations(status=status.HTTP_200_OK),
                )
                assert len(result.json()) == 0

    def create(self) -> ReadModelType:
        with self.subtests.test("create-organization"):
            create_result = self.scenario.create_organization(
                self.scenario.user1,
                organization=self.new_org.model_dump(mode="json"),
                expectations=Expectations(
                    status=status.HTTP_201_CREATED,
                    json=self.new_org.model_dump(mode="json"),
                ),
            )
            self.org_id = create_result.json()["id"]
            assert self.org_id
            with self.subtests.test("list-after-create"):
                result = self.scenario.list_organizations(
                    user=self.scenario.user1,
                    expectations=Expectations(status=status.HTTP_200_OK),
                )
                assert len(result.json()) == 1
                assert result.json()[0]["id"] == self.org_id

            with self.subtests.test("retrieve_after_create"):
                self.scenario.read_organization(
                    self.scenario.user1,
                    organization_id=self.org_id,
                    expectations=Expectations(
                        status=status.HTTP_200_OK,
                        json=create_result.json() | {"id": self.org_id},
                    ),
                )
            return Organization.schemas().read.model_validate(create_result.json())
        pytest.fail("failed to create organization.")

    def update(self) -> ReadModelType:
        assert self.org_id
        with self.subtests.test("update"):
            update_result = self.scenario.update_organization(
                user=self.scenario.user1,
                organization_id=self.org_id,
                organization=self.updated_org.model_dump(mode="json"),
                expectations=Expectations(
                    status=status.HTTP_200_OK,
                    json=self.updated_org.model_dump(mode="json") | {"id": self.org_id},
                ),
            )
            with self.subtests.test("retrieve_after_update"):
                self.scenario.read_organization(
                    self.scenario.user1,
                    organization_id=self.org_id,
                    expectations=Expectations(
                        status=status.HTTP_200_OK, json=update_result.json()
                    ),
                )
            return Organization.schemas().read.model_validate(update_result.json())
        pytest.fail("failed to update organization.")

    def delete(self) -> None:
        assert self.org_id
        with self.subtests.test("delete"):
            self.scenario.delete_organization(
                self.scenario.user1,
                organization_id=self.org_id,
                expectations=Expectations(status=status.HTTP_204_NO_CONTENT),
            )

    def post_delete(self) -> None:
        assert self.org_id
        with self.subtests.test("list-after-delete"):
            result = self.scenario.list_organizations(
                user=self.scenario.user1,
                expectations=Expectations(status=status.HTTP_200_OK),
            )
            assert len(result.json()) == 0
        with self.subtests.test("retrieve_after_delete"):
            self.scenario.read_organization(
                self.scenario.user1,
                organization_id=self.org_id,
                expectations=Expectations(status=status.HTTP_404_NOT_FOUND),
            )
        with self.subtests.test("update_after_delete"):
            self.scenario.update_organization(
                user=self.scenario.user1,
                organization_id=self.org_id,
                organization=self.updated_org.model_dump(mode="json"),
                expectations=Expectations(status=status.HTTP_404_NOT_FOUND),
            )
        with self.subtests.test("delete_after_delete"):
            self.scenario.delete_organization(
                self.scenario.user1,
                organization_id=self.org_id,
                expectations=Expectations(status=status.HTTP_404_NOT_FOUND),
            )

    def test_organization_crud_happy_path(self) -> None:
        self.pre_create()
        self.create()
        self.update()
        self.delete()
        self.post_delete()

    def test_created_field(self) -> None:
        self.pre_create()
        organization = self.create()
        initial_created = organization.created
        initial_updated = organization.updated
        organization = self.update()
        current_created = organization.created
        current_updated = organization.updated
        assert initial_created == current_created, (
            "created field should not change when updated"
        )
        assert initial_updated < current_updated, (
            "updated field should be newer after an update"
        )
