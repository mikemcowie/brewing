from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from polyfactory.factories.pydantic_factory import ModelFactory

from project_manager.organizations.models import Organization

if TYPE_CHECKING:
    from pytest_subtests import SubTests


def test_organization_crud(app: FastAPI, subtests: SubTests) -> None:
    client = TestClient(app)
    factory = ModelFactory.create_factory(Organization.schemas().create)
    update_factory = ModelFactory.create_factory(Organization.schemas().update)
    new_org = factory.build()
    with subtests.test("list-before"):
        result = client.get("/organizations/")
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 0

    with subtests.test("create-organization"):
        create_result = client.post(
            "/organizations/", json=new_org.model_dump(mode="json")
        )
        assert create_result.status_code == status.HTTP_201_CREATED
        org_id = create_result.json()["id"]
        with subtests.test("list-after-create"):
            result = client.get("/organizations/")
            assert result.status_code == status.HTTP_200_OK
            assert len(result.json()) == 1
            assert result.json()[0]["id"] == org_id
        with subtests.test("retrieve_after_create"):
            result = client.get(f"/organizations/{org_id}")
            assert result.status_code == status.HTTP_200_OK
            assert result.json() == create_result.json()
        update = update_factory.build()
        with subtests.test("update"):
            update_result = client.put(
                f"/organizations/{org_id}", json=update.model_dump(mode="json")
            )
            assert update_result.status_code == status.HTTP_200_OK
            with subtests.test("retrieve_after_update"):
                result = client.get(f"/organizations/{org_id}")
                assert result.status_code == status.HTTP_200_OK
                assert result.json() == update_result.json()
                assert result.json() != create_result.json()
        with subtests.test("delete"):
            delete_result = client.delete(f"/organizations/{org_id}")
            assert delete_result.status_code == status.HTTP_204_NO_CONTENT
            with subtests.test("list-before"):
                result = client.get("/organizations/")
                assert result.status_code == status.HTTP_200_OK
                assert len(result.json()) == 0
            with subtests.test("retrieve_after_delete"):
                result = client.get(f"/organizations/{org_id}")
                assert result.status_code == status.HTTP_404_NOT_FOUND
            with subtests.test("update_after_delete"):
                update_result = client.put(
                    f"/organizations/{org_id}", json=update.model_dump(mode="json")
                )
                assert update_result.status_code == status.HTTP_404_NOT_FOUND
            with subtests.test("delete_after_delete"):
                delete_result = client.delete(f"/organizations/{org_id}")
                assert delete_result.status_code == status.HTTP_404_NOT_FOUND
