from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from project_manager.exceptions import DomainError
from project_manager.settings import Settings
from project_manager.users.models import User
from project_manager.users.schemas import UserRead, UserRegister

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

    async def create_user(self, user: UserRegister) -> UserRead:
        async with self.db_session.begin():
            db_user = User(**user.model_dump())
            self.db_session.add(db_user)
            await self.db_session.flush()
            return UserRead.model_validate(db_user, from_attributes=True)
