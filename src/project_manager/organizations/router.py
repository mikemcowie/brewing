from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from project_manager import db
from project_manager.endpoints import Endpoints
from project_manager.exceptions import NotFound
from project_manager.organizations.models import Organization
from project_manager.resources.models import AccessLevel, ResourceAccess
from project_manager.users.models import User
from project_manager.users.router import user

router = APIRouter(tags=["organizations"], dependencies=[Depends(user)])


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


class OrganizationRepository:
    def __init__(self, session: AsyncSession, user: User):
        self.session = session
        self.user = user
        self.base_query = select(Organization).where(Organization.deleted == None)  # noqa: E711

    async def create(self, new_organization: CreateOrganization):
        organization = Organization(**new_organization.model_dump())
        access = ResourceAccess(
            resource=organization, user=self.user, access=AccessLevel.owner
        )
        self.session.add_all((organization, access))
        await self.session.commit()
        return OrganizationRead.model_validate(organization, from_attributes=True)

    async def list(self):
        return [
            OrganizationSummary.model_validate(org, from_attributes=True)
            for org in (await self.session.execute(self.base_query)).scalars()
        ]

    async def get(self, organization_id: UUID):
        if org := (
            await self.session.execute(
                self.base_query.where(Organization.id == organization_id)
            )
        ).scalar_one_or_none():
            return org
        raise NotFound(detail=f"{organization_id=!s} not found.")

    async def update(
        self,
        organization_id: UUID,
        update: UpdateOrganization,
    ) -> OrganizationRead:
        organization = await self.get(organization_id)
        for k, v in update.model_dump().items():
            setattr(organization, k, v)
        await self.session.commit()
        return OrganizationRead.model_validate(organization, from_attributes=True)

    async def delete(self, organization_id: UUID):
        org = await self.get(organization_id)
        org.deleted = datetime.now(UTC)
        await self.session.commit()


async def repo(db_session: DBSessionAnnotation, user: Annotated[User, Depends(user)]):
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
