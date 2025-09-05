from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from project_manager.db import Database
from project_manager.endpoints import Endpoints
from project_manager.models import User
from project_manager.settings import Settings

router = APIRouter(tags=["users"])


ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=Endpoints.USERS_LOGIN, auto_error=False)


class DomainError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "generic error"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.detail


class NotFound(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "resource not found"


class LoginFailure(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "incorrect username or password"


class Unauthorized(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "unauthorized"


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserRead(BaseModel):
    id: UUID
    username: str


class UserRegister(BaseModel):
    email: EmailStr
    password: SecretStr


class UserAuth:
    def __init__(
        self,
        db_session: AsyncSession,
        token: str | None = None,
        settings: Settings | None = None,
    ):
        self.db_session = db_session
        self.token = token or ""
        self.settings = settings or Settings()
        self.credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        self.password_context = CryptContext(schemes=["argon2"], deprecated="auto")

    def jwt_payload(self):
        if not self.token:
            raise Unauthorized()
        return jwt.decode(
            self.token,
            self.settings.SECRET_KEY.get_secret_value(),
            algorithms=[ALGORITHM],
        )

    def username_from_token(self):
        if username := self.jwt_payload().get("sub"):
            return username
        raise ValueError()

    async def user_from_db(self, user: str):
        result = (
            await self.db_session.execute(select(User).where(User.email == user))
        ).scalar_one_or_none()
        if result:
            return result
        raise NotFound(detail=f"{user=} not found")

    async def token_user(self):
        return await self.user_from_db(self.username_from_token())

    async def issue_token(self, username: str):
        return Token(
            access_token=jwt.encode(
                {
                    "sub": username,
                    "exp": datetime.now(UTC) + timedelta(ACCESS_TOKEN_EXPIRE_MINUTES),
                },
                self.settings.SECRET_KEY.get_secret_value(),
                ALGORITHM,
            ),
            token_type="bearer",
        )

    def hashed_password(self, value: str):
        return self.password_context.hash(value)

    def verify_password(self, plain_password: str, hashed_password: str):
        return self.password_context.verify(plain_password, hashed_password)

    async def authenticate(self, username: str, password: str):
        try:
            if self.verify_password(
                password, (await self.user_from_db(username)).password_hash
            ):
                return await self.issue_token(username)
        except NotFound:
            pass  # Don't show a 404 in this case, shpw a 401 by raising the next error.
        raise LoginFailure()

    async def create_user(self, user: UserRegister):
        user_data = user.model_dump() | {
            "password_hash": self.hashed_password(user.password.get_secret_value())
        }
        del user_data["password"]
        async with self.db_session.begin():
            db_user = User(**user_data)
            self.db_session.add(db_user)
            await self.db_session.flush()
            return UserRead.model_validate(db_user, from_attributes=True)


def settings():
    return Settings()


async def db_session(settings: Annotated[Settings, Depends(settings)]):
    async with Database(settings=settings).async_session() as session:
        yield session


async def user_auth(
    token: Annotated[str, Depends(oauth2_scheme)],
    db_session: Annotated[AsyncSession, Depends(db_session)],
):
    return UserAuth(token=token, db_session=db_session)


async def user(auth: Annotated[UserAuth, Depends(user_auth)]):
    return await auth.token_user()


@router.get(Endpoints.USERS_PROFILE)
async def user_own_profile(user: Annotated[User, Depends(user)]):
    return user


def secret_value(value: str | SecretStr):
    if isinstance(value, str):
        return value
    return value.get_secret_value()


@router.post(Endpoints.USERS_LOGIN)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth: Annotated[UserAuth, Depends(user_auth)],
):
    return await auth.authenticate(
        username=form.username, password=secret_value(form.password)
    )


@router.post(Endpoints.USERS_REGISTER, status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister, auth: Annotated[UserAuth, Depends(user_auth)]):
    return await auth.create_user(user)
