"""Tests for loaders"""

from dataclasses import dataclass
from datetime import datetime
from typing import Self

import pytest
from fastapi import FastAPI
from fastapi.exceptions import FastAPIError
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column

from brewing.http.serialization.loaders import TypeLoader

## Sqlalchemy models to be used in tests


class Base(DeclarativeBase):
    pass


class StandardDecModel(Base):
    """A declarative orm model with no special methods."""

    __tablename__ = "standard_dec_model"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    f1: Mapped[str] = mapped_column()
    f2: Mapped[str] = mapped_column()
    f3: Mapped[datetime] = mapped_column()

    # This class won't be able to be loaded through its init method
    # because the default __init_ method on declarative base uses only **kwargs
    # and has no usable type hints.
    # But it should be able to be loaded through our machinery via
    # factory functions including these classmethods, as long as these classmethods
    # have appopriate return annotation.

    # Self should work as return annotation
    @classmethod
    def load_with_self_annotation(cls, f1: str, f2: str) -> Self:
        return cls(f1=f1, f2=f2)

    # As should the model itself
    @classmethod
    def load_with_exact_annotation(cls, f1: str, f2: str) -> StandardDecModel:
        return cls(f1=f1, f2=f2)

    # But this will not be handled as it lacks a return annotation.
    @classmethod
    def load_with_no_annotation(cls, f1: str, f2: str):
        return cls(f1=f1, f2=f2)


class CustomInitModel(Base):
    __tablename__ = "custom_init_model"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    f1: Mapped[str] = mapped_column()
    f2: Mapped[str] = mapped_column()
    f3: Mapped[datetime] = mapped_column()

    def __init__(self, f1: str, f2: str):
        self.f1 = f1
        self.f2 = f2


class DataclassMappedModel(MappedAsDataclass, Base):
    __tablename__ = "dataclass_dec_model"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
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
        ) == ["f1", "f2"]
        client = TestClient(app)
        with pytest.raises(AttributeError):
            client.post("/mapped_dataclass", json={"f1": "foo", "f2": "bar"})


class TestTypeLoader:
    def test_type_loader_on_sqlalchemy_model_with_no_init(self):
        with pytest.raises(TypeError) as error:
            TypeLoader(StandardDecModel)

        assert (
            "function must accept at least 1 named keyword argument"
        ) in error.exconly()

    def test_type_loader_on_sqlalchemy_model_with_init(self):
        class CustomInitModelSchema(BaseModel):
            f1: str
            f2: str

        loader = TypeLoader(CustomInitModel)
        assert (
            loader.model.model_json_schema()
            == CustomInitModelSchema.model_json_schema()
        )

    def test_type_loader_on_sqlalchemy_model_with_mapped_as_dataclass(self):
        class DataclassMappedModelSchema(BaseModel):
            f1: str
            f2: str

        loader = TypeLoader(DataclassMappedModel)
        assert (
            loader.model.model_json_schema()
            == DataclassMappedModelSchema.model_json_schema()
        )

    def test_type_loader_with_arbitary_python_class_without_init(self):
        class SomeClass:
            f1: str
            f2: str

        with pytest.raises(TypeError) as error:
            TypeLoader(SomeClass)

        assert "no __init__ method" in error.exconly()

    def test_type_loader_with_standard_dataclass(self):
        @dataclass
        class SomeClass:
            f1: str
            f2: str

        class SomeClassSchema(BaseModel):
            f1: str
            f2: str

        loader = TypeLoader(SomeClass)
        assert loader.model.model_json_schema() == SomeClassSchema.model_json_schema()

    def test_type_loader_with_arbitary_python_class_with_untyped_init(self):
        class SomeClass:
            def __init__(self, f1, f2: str):  # type: ignore
                self.f1 = f1  # type: ignore
                self.f2 = f2

        with pytest.raises(TypeError) as error:
            TypeLoader(SomeClass)

        assert "missing type annotation" in error.exconly()

    def test_type_loader_with_factory_function(self):
        def make_instance(f1: str, f2: str) -> StandardDecModel:
            return StandardDecModel(f1=f1, f2=f2)

        class StandardDecModelSchema(BaseModel):
            f1: str
            f2: str

        loader = TypeLoader(make_instance)
        assert (
            loader.model.model_json_schema()
            == StandardDecModelSchema.model_json_schema()
        )

    def test_type_loader_with_factory_function_lacking_return_annotation(self):
        def make_instance(f1: str, f2: str) -> StandardDecModel:
            return StandardDecModel(f1=f1, f2=f2)

        with pytest.raises(TypeError) as error:
            TypeLoader(make_instance)
        assert "No return annotation" in error.exconly()

    def test_type_loader_with_classmethod(self):
        class StandardDecModelSchema(BaseModel):
            f1: str
            f2: str

        loader = TypeLoader(StandardDecModel.load_with_exact_annotation)
        assert (
            loader.model.model_json_schema()
            == StandardDecModelSchema.model_json_schema()
        )

    def test_type_loader_with_classmethod_self(self):
        class StandardDecModelSchema(BaseModel):
            f1: str
            f2: str

        loader = TypeLoader(StandardDecModel.load_with_self_annotation)
        assert (
            loader.model.model_json_schema()
            == StandardDecModelSchema.model_json_schema()
        )

    def test_type_loader_with_no_annotation(self):
        with pytest.raises(TypeError):
            TypeLoader(StandardDecModel.load_with_self_annotation)
