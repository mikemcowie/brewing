from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from project_manager import db
from project_manager.endpoints import Endpoints
from project_manager.exceptions import NotFound
from project_manager.organizations.models import Organization

router = APIRouter(tags=["organizations"])


DBSessionAnnotation = Annotated[AsyncSession, Depends(db.db_session)]

if TYPE_CHECKING:  # Type checker type hints (just that its a model)
    from pydantic import BaseModel

    OrganizationRead = BaseModel
    OrganizationSummary = BaseModel
    CreateOrganization = BaseModel
    UpdateOrganization = BaseModel
else:  # At runtime we derive these from the sqlalchemy mapped class
    OrganizationRead = Organization.schemas().read
    OrganizationSummary = Organization.schemas().summary
    CreateOrganization = Organization.schemas().create
    UpdateOrganization = Organization.schemas().update


@router.post(Endpoints.ORGANIZATIONS)  # response_model=OrganizationRead)
async def create_organization(
    create: CreateOrganization, db_session: DBSessionAnnotation
) -> OrganizationRead:
    organization = Organization(**create.model_dump())
    db_session.add(organization)
    await db_session.flush()
    return OrganizationRead.model_validate(organization, from_attributes=True)


@router.get(Endpoints.ORGANIZATIONS, response_model=list[OrganizationSummary])
async def list_organization(
    db_session: DBSessionAnnotation,
) -> list[OrganizationSummary]:
    return [
        OrganizationSummary.model_validate(org, from_attributes=True)
        for org in (await db_session.execute(select(Organization))).scalars()
    ]


async def organization(
    organization_id: UUID, db_session: DBSessionAnnotation
) -> Organization:
    if org := (
        await db_session.execute(
            select(Organization).where(Organization.id == organization_id)
        )
    ).scalar_one_or_none():
        return org
    raise NotFound(detail=f"{organization_id=!s} not found.")


OrganizationAnnotation = Annotated[Organization, Depends(organization)]


@router.get(Endpoints.ORGANIZATIONS_ONE, response_model=OrganizationRead)
async def read_organization(organization: OrganizationAnnotation) -> OrganizationRead:
    return OrganizationRead.model_validate(organization, from_attributes=True)


@router.put(Endpoints.ORGANIZATIONS_ONE, response_model=OrganizationRead)
async def update_organization(
    organization: OrganizationAnnotation,
    update: UpdateOrganization,
    db_session: DBSessionAnnotation,
) -> OrganizationRead:
    for k, v in update.model_dump().items():
        setattr(organization, k, v)
    await db_session.commit()
    return OrganizationRead.model_validate(organization, from_attributes=True)


@router.delete(Endpoints.ORGANIZATIONS_ONE)
async def delete_organization(
    db_session: DBSessionAnnotation, organization: OrganizationAnnotation
) -> None:
    await db_session.delete(organization)
    await db_session.commit()
