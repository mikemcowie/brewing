from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column

from project_manager.resources.models import Resource


class Organization(Resource, kw_only=True):
    summary_fields = (*list(Resource.summary_fields), "name")
    id: Mapped[UUID] = Resource.primary_foreign_key_to()
    name: Mapped[str] = mapped_column(index=True)


# org = Organization()
