from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from project_manager import db
from project_manager.endpoints import Endpoints
from project_manager.organizations.repo import (
    CreateOrganization,
    OrganizationRead,
    OrganizationRepository,
    OrganizationSummary,
    UpdateOrganization,
)
from project_manager.users.models import User
from project_manager.users.router import user

router = APIRouter(tags=["organizations"], dependencies=[Depends(user)])


async def repo(
    db_session: Annotated[AsyncSession, Depends(db.db_session)],
    user: Annotated[User, Depends(user)],
):
    return OrganizationRepository(db_session, user)


@router.post(
    Endpoints.ORGANIZATIONS, status_code=status.HTTP_201_CREATED
)  # response_model=OrganizationRead)
async def create_organization(
    create: CreateOrganization, repo: Annotated[OrganizationRepository, Depends(repo)]
) -> OrganizationRead:
    return await repo.create(create)


@router.get(Endpoints.ORGANIZATIONS, response_model=list[OrganizationSummary])
async def list_organization(
    repo: Annotated[OrganizationRepository, Depends(repo)],
) -> list[OrganizationSummary]:
    return await repo.list()


@router.get(Endpoints.ORGANIZATIONS_ONE, response_model=OrganizationRead)
async def read_organization(
    organization_id: UUID, repo: Annotated[OrganizationRepository, Depends(repo)]
) -> OrganizationRead:
    return OrganizationRead.model_validate(
        await repo.get(organization_id), from_attributes=True
    )


@router.put(Endpoints.ORGANIZATIONS_ONE, response_model=OrganizationRead)
async def update_organization(
    organization_id: UUID,
    update: UpdateOrganization,
    repo: Annotated[OrganizationRepository, Depends(repo)],
) -> OrganizationRead:
    return await repo.update(organization_id, update)


@router.delete(Endpoints.ORGANIZATIONS_ONE, status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: UUID,
    repo: Annotated[OrganizationRepository, Depends(repo)],
) -> None:
    await repo.delete(organization_id)
