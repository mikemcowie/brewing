from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from cauldron.resources.models import AccessLevel, Resource, ResourceAccessItem
from fastapi import FastAPI, status
from polyfactory.factories.pydantic_factory import ModelFactory
from project_manager.app import Organization

from tests.api.scenario import Expectations, User
from tests.api.test_user import UserTestScenario

if TYPE_CHECKING:
    from cauldron.resources.models import ReadModelType
    from httpx import Response
    from polyfactory.factories import BaseFactory
    from pydantic import BaseModel
    from pytest_subtests import SubTests


class ResourceTestScenario[ModelT: Resource](UserTestScenario):
    db_model: type[ModelT]

    @property
    def base_path(self):
        return f"/{self.db_model.plural_name}/"

    def __class_getitem__(cls, resource_type: type[Resource]):
        return type(cls.__name__, (cls,), {"db_model": resource_type})

    def list_resources(self, user: User, expectations: Expectations) -> Response:
        result = user.client.get(self.base_path)
        self.validate_expectations(expectations, result)
        return result

    def create_resource(
        self, user: User, resource: dict[str, Any], expectations: Expectations
    ) -> Response:
        result = user.client.post(self.base_path, json=resource)
        self.validate_expectations(expectations, result)
        return result

    def update_resource(
        self,
        user: User,
        resource_id: str,
        resource: dict[str, Any],
        expectations: Expectations,
    ) -> Response:
        result = user.client.put(f"{self.base_path}{resource_id}", json=resource)
        self.validate_expectations(expectations, result)
        return result

    def read_resource(
        self, user: User, resource_id: str, expectations: Expectations
    ) -> Response:
        result = user.client.get(f"{self.base_path}{resource_id}")
        self.validate_expectations(expectations, result)
        return result

    def delete_resource(
        self, user: User, resource_id: str, expectations: Expectations
    ) -> Response:
        result = user.client.delete(f"{self.base_path}{resource_id}")
        self.validate_expectations(expectations, result)
        return result

    def read_access(
        self, user: User, resource_id: str, expectations: Expectations
    ) -> Response:
        result = user.client.get(f"{self.base_path}{resource_id}/access/")
        self.validate_expectations(expectations, result)
        return result

    def read_access_one(
        self, user: User, resource_id: str, user_id: str, expectations: Expectations
    ) -> Response:
        result = user.client.get(f"{self.base_path}{resource_id}/access/{user_id}")
        self.validate_expectations(expectations, result)
        return result

    def set_access(
        self,
        user: User,
        access: ResourceAccessItem | list[ResourceAccessItem],
        resource_id: str,
        expectations: Expectations,
    ):
        access = [access] if not isinstance(access, list) else access
        result = user.client.post(
            f"{self.base_path}{resource_id}/access/",
            json=[a.model_dump(mode="json") for a in access],
        )
        self.validate_expectations(expectations, result)
        return result


class BaseTestResourceCrud[ModelT: Resource]:
    def __class_getitem__(cls, model: type[Resource]):
        return type(cls.__name__, (cls,), {"model": model})

    model: type[ModelT]

    @pytest.fixture(autouse=True)
    def scenario_fixture(
        self, subtests: SubTests, app: FastAPI
    ) -> ResourceTestScenario[ModelT]:
        self.scenario = ResourceTestScenario[self.model](subtests=subtests, app=app)
        self.subtests = subtests
        self.app = app
        self.bar = None
        self.resource_id: str | None = None
        return self.scenario

    @cached_property
    def factory(self) -> type[BaseFactory[BaseModel]]:
        return ModelFactory.create_factory(self.model.schemas().create)

    @cached_property
    def update_factory(self) -> type[BaseFactory[BaseModel]]:
        return ModelFactory.create_factory(self.model.schemas().create)

    @cached_property
    def new_resource(self) -> BaseModel:
        return self.factory.build()

    @cached_property
    def updated_resource(self) -> BaseModel:
        return self.update_factory.build()

    def pre_create(self) -> None:
        with self.subtests.test("prepare-users"):
            self.scenario.register_all_users()
            self.scenario.login_all_users()
            with self.subtests.test("list-before"):
                result = self.scenario.list_resources(
                    user=self.scenario.user1,
                    expectations=Expectations(status=status.HTTP_200_OK),
                )
                assert len(result.json()) == 0

    def create(self) -> ReadModelType:
        with self.subtests.test("create-resource"):
            create_result = self.scenario.create_resource(
                self.scenario.user1,
                resource=self.new_resource.model_dump(mode="json"),
                expectations=Expectations(
                    status=status.HTTP_201_CREATED,
                    json=self.new_resource.model_dump(mode="json"),
                ),
            )
            self.resource_id = create_result.json()["id"]
            assert self.resource_id
            with self.subtests.test("list-after-create"):
                result = self.scenario.list_resources(
                    user=self.scenario.user1,
                    expectations=Expectations(status=status.HTTP_200_OK),
                )
                assert len(result.json()) == 1
                assert result.json()[0]["id"] == self.resource_id

            with self.subtests.test("retrieve_after_create"):
                self.scenario.read_resource(
                    self.scenario.user1,
                    resource_id=self.resource_id,
                    expectations=Expectations(
                        status=status.HTTP_200_OK,
                        json=create_result.json() | {"id": self.resource_id},
                    ),
                )
            return Organization.schemas().read.model_validate(create_result.json())
        pytest.fail("failed to create resource.")

    def update(self) -> ReadModelType:
        assert self.resource_id
        with self.subtests.test("update"):
            update_result = self.scenario.update_resource(
                user=self.scenario.user1,
                resource_id=self.resource_id,
                resource=self.updated_resource.model_dump(mode="json"),
                expectations=Expectations(
                    status=status.HTTP_200_OK,
                    json=self.updated_resource.model_dump(mode="json")
                    | {"id": self.resource_id},
                ),
            )
            with self.subtests.test("retrieve_after_update"):
                self.scenario.read_resource(
                    self.scenario.user1,
                    resource_id=self.resource_id,
                    expectations=Expectations(
                        status=status.HTTP_200_OK, json=update_result.json()
                    ),
                )
            return Organization.schemas().read.model_validate(update_result.json())
        pytest.fail("failed to update resource.")

    def delete(self) -> None:
        assert self.resource_id
        with self.subtests.test("delete"):
            self.scenario.delete_resource(
                self.scenario.user1,
                resource_id=self.resource_id,
                expectations=Expectations(status=status.HTTP_204_NO_CONTENT),
            )

    def post_delete(self) -> None:
        assert self.resource_id
        with self.subtests.test("list-after-delete"):
            result = self.scenario.list_resources(
                user=self.scenario.user1,
                expectations=Expectations(status=status.HTTP_200_OK),
            )
            assert len(result.json()) == 0
        with self.subtests.test("retrieve_after_delete"):
            self.scenario.read_resource(
                self.scenario.user1,
                resource_id=self.resource_id,
                expectations=Expectations(status=status.HTTP_404_NOT_FOUND),
            )
        with self.subtests.test("update_after_delete"):
            self.scenario.update_resource(
                user=self.scenario.user1,
                resource_id=self.resource_id,
                resource=self.updated_resource.model_dump(mode="json"),
                expectations=Expectations(status=status.HTTP_404_NOT_FOUND),
            )
        with self.subtests.test("delete_after_delete"):
            self.scenario.delete_resource(
                self.scenario.user1,
                resource_id=self.resource_id,
                expectations=Expectations(status=status.HTTP_404_NOT_FOUND),
            )

    def test_resource_crud_happy_path(self) -> None:
        self.pre_create()
        self.create()
        self.update()
        self.delete()
        self.post_delete()

    def test_created_field(self) -> None:
        self.pre_create()
        resource = self.create()
        initial_created = resource.created
        initial_updated = resource.updated
        resource = self.update()
        current_created = resource.created
        current_updated = resource.updated
        assert initial_created == current_created, (
            "created field should not change when updated"
        )
        assert initial_updated < current_updated, (
            "updated field should be newer after an update"
        )

    def test_cannot_modify_org_if_not_member(self):
        self.pre_create()
        org = self.create()
        self.scenario.update_resource(
            self.scenario.user2,
            str(org.id),
            self.updated_resource.model_dump(mode="json"),
            Expectations(status=status.HTTP_404_NOT_FOUND),
        )

    def test_user_is_owner_after_create(self):
        self.pre_create()
        org = self.create()
        access = self.scenario.read_access(
            self.scenario.user1,
            resource_id=str(org.id),
            expectations=Expectations(status=status.HTTP_200_OK),
        )
        assert isinstance(access.json(), list)
        assert len(access.json()) == 1
        user_id = self.scenario.retrieve_profile(
            self.scenario.user1,
            "test-user-is-owner-find_user_id",
            expectations=Expectations(),
        ).json()["id"]
        assert access.json()[0]["user_id"] == user_id
        assert access.json()[0]["access"] == "owner"

    def user1_assigns_user2_access(self, level: AccessLevel = AccessLevel.owner):
        self.pre_create()
        org = self.create()
        user2_id = self.scenario.retrieve_profile(
            self.scenario.user2, "test-user2-access-read", expectations=Expectations()
        ).json()["id"]
        self.scenario.set_access(
            self.scenario.user1,
            access=[ResourceAccessItem(user_id=UUID(user2_id), access=level)],
            expectations=Expectations(),
            resource_id=str(org.id),
        )
        access = self.scenario.read_access(
            self.scenario.user1,
            resource_id=str(org.id),
            expectations=Expectations(status=status.HTTP_200_OK),
        )
        assert len(access.json()) == 2
        assert user2_id in [a["user_id"] for a in access.json()]
        self.scenario.read_access_one(
            self.scenario.user1,
            resource_id=str(org.id),
            user_id=user2_id,
            expectations=Expectations(
                status=status.HTTP_200_OK,
                json={"user_id": user2_id, "access": level.value},
            ),
        )
        return org

    def test_reader_access(self):
        org = self.user1_assigns_user2_access(AccessLevel.reader)
        user2_id = self.scenario.retrieve_profile(
            self.scenario.user2, "test-user2-access-read", expectations=Expectations()
        ).json()["id"]
        self.scenario.read_resource(
            self.scenario.user2, str(org.id), Expectations(status=status.HTTP_200_OK)
        )
        self.scenario.update_resource(
            self.scenario.user2,
            str(org.id),
            self.updated_resource.model_dump(mode="json"),
            Expectations(status=status.HTTP_401_UNAUTHORIZED),
        )
        self.scenario.delete_resource(
            self.scenario.user2,
            str(org.id),
            Expectations(status=status.HTTP_401_UNAUTHORIZED),
        )
        self.scenario.read_access(
            self.scenario.user2,
            str(org.id),
            Expectations(status=status.HTTP_401_UNAUTHORIZED),
        )
        self.scenario.set_access(
            self.scenario.user2,
            [ResourceAccessItem(user_id=UUID(user2_id), access=AccessLevel.owner)],
            str(org.id),
            Expectations(status=status.HTTP_401_UNAUTHORIZED),
        )

    def test_contributor_access(self):
        org = self.user1_assigns_user2_access(AccessLevel.contributor)
        user2_id = self.scenario.retrieve_profile(
            self.scenario.user2, "test-user2-access-read", expectations=Expectations()
        ).json()["id"]
        self.scenario.read_resource(
            self.scenario.user2, str(org.id), Expectations(status=status.HTTP_200_OK)
        )
        self.scenario.update_resource(
            self.scenario.user2,
            str(org.id),
            self.updated_resource.model_dump(mode="json"),
            Expectations(status=status.HTTP_200_OK),
        )
        self.scenario.delete_resource(
            self.scenario.user2,
            str(org.id),
            Expectations(status=status.HTTP_401_UNAUTHORIZED),
        )
        self.scenario.read_access(
            self.scenario.user2,
            str(org.id),
            Expectations(status=status.HTTP_200_OK),
        )
        self.scenario.set_access(
            self.scenario.user2,
            [ResourceAccessItem(user_id=UUID(user2_id), access=AccessLevel.owner)],
            str(org.id),
            Expectations(status=status.HTTP_401_UNAUTHORIZED),
        )

    def test_owner_access(self):
        org = self.user1_assigns_user2_access(AccessLevel.owner)
        user2_id = self.scenario.retrieve_profile(
            self.scenario.user2, "test-user2-access-read", expectations=Expectations()
        ).json()["id"]
        self.scenario.read_resource(
            self.scenario.user2, str(org.id), Expectations(status=status.HTTP_200_OK)
        )
        self.scenario.update_resource(
            self.scenario.user2,
            str(org.id),
            self.updated_resource.model_dump(mode="json"),
            Expectations(status=status.HTTP_200_OK),
        )
        self.scenario.delete_resource(
            self.scenario.user2,
            str(org.id),
            Expectations(status=status.HTTP_204_NO_CONTENT),
        )
        self.scenario.read_access(
            self.scenario.user2,
            str(org.id),
            Expectations(status=status.HTTP_200_OK),
        )
        self.scenario.set_access(
            self.scenario.user2,
            [ResourceAccessItem(user_id=UUID(user2_id), access=AccessLevel.owner)],
            str(org.id),
            Expectations(status=status.HTTP_200_OK),
        )


class TestOrganization(BaseTestResourceCrud[Organization]):
    pass
