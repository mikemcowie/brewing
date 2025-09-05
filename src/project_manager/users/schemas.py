from uuid import UUID

from pydantic import BaseModel, EmailStr, SecretStr


class UserRead(BaseModel):
    id: UUID
    username: str


class UserRegister(BaseModel):
    email: EmailStr
    password: SecretStr
