from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, SecretStr


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserRead(BaseModel):
    id: UUID
    username: str


class UserRegister(BaseModel):
    email: EmailStr
    password: SecretStr
