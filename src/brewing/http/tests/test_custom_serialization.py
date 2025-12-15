from __future__ import annotations

from datetime import datetime
from functools import cached_property
from typing import Annotated, Self
from uuid import uuid7

import pytest
from fastapi import FastAPI
from fastapi.exceptions import FastAPIError
from fastapi.testclient import TestClient
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column

from brewing.http import ViewSet, root, status
from brewing.http.serialization.loaders import TypeLoader
from brewing.http.testing import new_client

## Sqlalchemy models to be used in tests


class Base(DeclarativeBase):
    pass


class StandardDecModel(Base):
    """A declarative orm model with no special methods."""

    __tablename__ = "ser_standard_dec_model"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    f1: Mapped[str] = mapped_column()
    f2: Mapped[str] = mapped_column()
    f3: Mapped[datetime] = mapped_column()

    @classmethod
    def load(cls, f1: str, f2: str) -> Self:
        return cls(f1=f1, f2=f2)


class CustomInitModel(Base):
    __tablename__ = "ser_custom_init_model"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    f1: Mapped[str] = mapped_column()
    f2: Mapped[str] = mapped_column()
    f3: Mapped[datetime] = mapped_column()

    def __init__(self, f1: str, f2: str):
        self.f1 = f1
        self.f2 = f2


class DataclassMappedModel(MappedAsDataclass, Base):
    __tablename__ = "ser_dataclass_dec_model"
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, init=False, default_factory=uuid7
    )
    f1: Mapped[str] = mapped_column()
    f2: Mapped[str] = mapped_column()
    f3: Mapped[datetime] = mapped_column(init=False)


class TestFastAPI:
    """Explorative: getting to grips with how fastapi behaves with these if we change nothing.

    This is less testing brewing, more documenting the baseline fastapi behaviour
    that brewing needs to override in order to use sqlalchemy models as request or respons models.
    """

    def test_schema_basic_declarative_class_as_body_annotation(self):
        # Fastapi won't touch a declarative base model
        app = FastAPI()
        db = []

        with pytest.raises(FastAPIError):

            @app.post("/standard", response_model=None)
            def create_standard_dev_model(item: StandardDecModel) -> str:
                db.append(item)
                return "done"

    def test_custom_init(self):
        # Defing __init__ on the model doesn't help
        app = FastAPI()
        db = []

        with pytest.raises(FastAPIError):

            @app.post("/custom_init", response_model=None)
            def create_custom_init_model(item: CustomInitModel) -> str:
                db.append(item)
                return "done"

    def test_mapped_as_dataclass(self):
        # With MappedAsDataclass, it will load the model into the app with a valid schema
        # But will fail at runtime as it doesn't naturally work with fastapi's parsing.
        app = FastAPI()
        db = []

        @app.post("/mapped_dataclass", response_model=None)
        def create_dataclass_model(item: DataclassMappedModel) -> str:
            db.append(item)
            return "done"

        assert (
            app.openapi()["paths"]["/mapped_dataclass"]["post"]["requestBody"][
                "content"
            ]["application/json"]["schema"]["$ref"]
            == "#/components/schemas/DataclassMappedModel"
        )
        assert list(
            app.openapi()["components"]["schemas"]["DataclassMappedModel"][
                "properties"
            ].keys()
        ) == ["id", "f1", "f2"]
        client = TestClient(app)
        with pytest.raises(AttributeError):
            client.post("/mapped_dataclass", json={"f1": "foo", "f2": "bar"})


class TestDeclaratieWithInit:
    @cached_property
    def viewset(self):
        class TestViewset(ViewSet):
            test1 = root("test1")

            @test1.POST()
            def create(
                self, item: Annotated[CustomInitModel, TypeLoader(CustomInitModel)]
            ):  # -> CustomInitModel:
                assert isinstance(item, CustomInitModel), type(item).__mro__
                return item

        return TestViewset()

    @cached_property
    def client(self):
        return new_client(self.viewset)

    def test_loader(self):
        result = self.client.post("/test1", json={"f1": "foo", "f2": "bar"})
        assert result.status_code == status.HTTP_200_OK, result.json()
        assert result.json()["f1"] == "foo"
        assert result.json()["f2"] == "bar"
        assert list(result.json().keys()) == ["f1", "f2"]

    def test_invalid_payload(self):
        result = self.client.post("/test1", json={"f1": "foo"})
        assert result.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestNoInit:
    @cached_property
    def viewset(self):
        class TestViewset(ViewSet):
            test1 = root("test1")

            @test1.POST()
            def create(
                self, item: Annotated[StandardDecModel, TypeLoader(StandardDecModel)]
            ):  # -> CustomInitModel:
                assert isinstance(item, StandardDecModel), type(item).__mro__
                return item

        return TestViewset()

    @cached_property
    def client(self):
        return new_client(self.viewset)

    def test_basic_loader(self):
        with pytest.raises(TypeError) as error:
            _ = self.viewset

        assert (
            " function must accept at least 1 named keyword argument (not **kwargs) in  __init__"
            in error.exconly()
        )


class TestMappedAsDataclass:
    @cached_property
    def viewset(self):
        class TestViewset(ViewSet):
            test1 = root("test1")

            @test1.POST()
            def create(
                self,
                item: Annotated[DataclassMappedModel, TypeLoader(DataclassMappedModel)],
            ):  # -> CustomInitModel:
                assert isinstance(item, DataclassMappedModel), type(item).__mro__
                return item

        return TestViewset()

    @cached_property
    def client(self):
        return new_client(self.viewset)

    def test_basic_load(self):
        result = self.client.post("/test1", json={"f1": "foo", "f2": "bar"})
        assert result.status_code == status.HTTP_200_OK, result.json()
        assert result.json()["f1"] == "foo"
        assert result.json()["f2"] == "bar"
        assert list(result.json().keys()) == ["id", "f1", "f2", "f3"]

    def test_load_invalid(self):
        result = self.client.post("/test1", json={"f1": "foo"})
        assert result.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
