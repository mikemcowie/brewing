from __future__ import annotations

import uuid

from sqlalchemy.orm import Mapped, mapped_column

from cauldron.resources.models import Resource

UUID = uuid.UUID


class Organization(Resource, kw_only=True):
    plural_name = "organizations"
    singular_name = "organization"
    summary_fields = (*list(Resource.summary_fields), "name")
    id: Mapped[UUID] = Resource.primary_foreign_key_to(init=False)
    name: Mapped[str] = mapped_column(index=True)


# org = Organization()
