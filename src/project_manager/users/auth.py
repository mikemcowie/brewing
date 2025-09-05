from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from project_manager.exceptions import DomainError
from project_manager.settings import Settings
from project_manager.users.models import (
    Token,
    User,
    UserRead,
    UserRegister,
    UserSession,
)

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12
ALGORITHM = "HS256"


class LoginFailure(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "incorrect username or password"


class InvalidToken(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "invalid token."


class UserAuth:
    def __init__(
        self,
        db_session: AsyncSession,
        token: Token | None,
        settings: Settings | None = None,
    ) -> None:
        self.db_session = db_session
        self.token = token or None
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

    async def authenticated_user(self) -> User | None:
        if not self.token:
            return None
        user_session = await UserSession.validated(self.token, self.db_session)
        if user_session:
            return user_session.user
        raise InvalidToken(detail="invalid token")

    async def login(self, username: str, password: str) -> Token:
        return await User.authorize(self.db_session, username, password)
