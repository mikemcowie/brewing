from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from project_manager.exceptions import DomainError, NotFound, Unauthorized
from project_manager.settings import Settings
from project_manager.users.models import User
from project_manager.users.schemas import Token, UserRead, UserRegister

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12
ALGORITHM = "HS256"


class LoginFailure(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "incorrect username or password"


class UserAuth:
    def __init__(
        self,
        db_session: AsyncSession,
        token: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.db_session = db_session
        self.token = token or ""
        self.settings = settings or Settings()
        self.credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        self.password_context = CryptContext(schemes=["argon2"], deprecated="auto")

    def jwt_payload(self) -> dict[str, str]:
        if not self.token:
            raise Unauthorized()
        result: dict[str, str] = jwt.decode(
            self.token,
            self.settings.SECRET_KEY.get_secret_value(),
            algorithms=[ALGORITHM],
        )
        return result

    def username_from_token(self) -> str:
        if username := self.jwt_payload().get("sub"):  # pragma: no branch
            return username
        raise ValueError("sub not found in token")  # pragma: no cover

    async def user_from_db(self, user: str) -> User:
        result = (
            await self.db_session.execute(select(User).where(User.email == user))
        ).scalar_one_or_none()
        if result:
            return result
        raise NotFound(detail=f"{user=} not found")

    async def token_user(self) -> User:
        return await self.user_from_db(self.username_from_token())

    async def issue_token(self, username: str) -> Token:
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

    def hashed_password(self, value: str) -> str:
        return self.password_context.hash(value)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.password_context.verify(plain_password, hashed_password)

    async def authenticate(self, username: str, password: str) -> Token:
        try:
            if self.verify_password(
                password, (await self.user_from_db(username)).password_hash
            ):
                return await self.issue_token(username)
        except NotFound:
            pass  # Don't show a 404 in this case, shpw a 401 by raising the next error.
        raise LoginFailure()

    async def create_user(self, user: UserRegister) -> UserRead:
        user_data = user.model_dump() | {
            "password_hash": self.hashed_password(user.password.get_secret_value())
        }
        del user_data["password"]
        async with self.db_session.begin():
            db_user = User(**user_data)
            self.db_session.add(db_user)
            await self.db_session.flush()
            return UserRead.model_validate(db_user, from_attributes=True)
