from __future__ import annotations

import uuid

from cauldron.resources.models import Resource
from sqlalchemy.orm import Mapped, mapped_column

UUID = uuid.UUID


class Organization(Resource, kw_only=True):
    plural_name = "organizations"
    singular_name = "organization"
    summary_fields = (*list(Resource.summary_fields), "name")
    id: Mapped[UUID] = Resource.primary_foreign_key_to(init=False)
    name: Mapped[str] = mapped_column(index=True)
