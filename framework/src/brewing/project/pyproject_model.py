"""A pydantic model for the data in pyproject.toml."""

from typing import Any
from pydantic import BaseModel, Field, model_validator, RootModel, field_validator


class ProjectAuthor(BaseModel):
    """The author field of the project table."""

    name: str | None = None
    email: str | None = None

    @model_validator(mode="after")
    def at_least_one_defined(self):
        """At least one of email or name must be provided."""
        if not self.name and not self.email:
            raise ValueError("At least one of email or name must be provided.")
        return self


class Project(BaseModel):
    """The project table data in pyproject.toml."""

    name: str | None = None
    description: str | None = None
    readme: str | None = None
    version: str | None = None
    dependencies: list[str] | None = None
    requires_python: str | None = Field(
        default=None, serialization_alias="requires-python"
    )
    authors: list[ProjectAuthor] | None = None
    license: str | None = None
    keywords: list[str] | None = None
    classifiers: list[str] | None = None
    urls: RootModel[dict[str, str]] | None = None
    entry_points: RootModel[dict[str, dict[str, str]]] | None = Field(
        default=None, serialization_alias="entry-points"
    )
    scripts: RootModel[dict[str, str]] | None = None

    @field_validator("name", mode="after")
    @classmethod
    def valid_name(cls, value: str):
        """Ensure the name field is valid."""
        return value.replace("_", "-")


class BuildSystem(BaseModel):
    """The build-system table."""

    requires: list[str]
    build_backend: str = Field(default=..., serialization_alias="build-backend")


class PyprojectTomlData(BaseModel):
    """Schema of pyproject.toml."""

    project: Project
    build_system: BuildSystem = Field(default=..., serialization_alias="build-system")
    tool: RootModel[dict[str, Any]] | None = None
