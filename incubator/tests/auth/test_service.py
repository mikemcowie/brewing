from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from brewing_incubator.auth.exceptions import InvalidToken
from brewing_incubator.auth.users import UserService
from brewing_incubator.exceptions import Unauthorized
from fastapi.requests import Request


@pytest.mark.asyncio
async def test_user_from_request():
    user = object()

    class FakeRepo:
        def __init__(self, *_, **__):  # type: ignore
            pass

        async def validated(self, token: str):  # noqa
            return SimpleNamespace(user=user)

    svc = UserService[FakeRepo, Mock](AsyncMock())  # type: ignore
    svc.token = AsyncMock()
    svc.token.return_value = "TOKEN"

    assert await svc.user_from_request(Request({"type": "http"})) is user


@pytest.mark.asyncio
async def test_user_from_request_if_none_returned_by_repo():
    user = object()

    class FakeRepo:
        def __init__(self, *_, **__):  # type: ignore
            pass

        async def validated(self, token: str):  # noqa: ARG002
            return None

    svc = UserService[FakeRepo, Mock](AsyncMock())  # type: ignore
    svc.token = AsyncMock()
    svc.token.return_value = "TOKEN"

    with pytest.raises(InvalidToken):
        assert await svc.user_from_request(Request({"type": "http"})) is user


@pytest.mark.asyncio
async def test_user_from_request_if_no_token_in_request():
    user = object()

    class FakeRepo:
        def __init__(self, *_, **__):  # type: ignore
            pass

        async def validated(self, token: str):  # noqa: ARG002
            return SimpleNamespace(user=user)

    svc = UserService[FakeRepo, Mock](AsyncMock())  # type: ignore
    svc.token = AsyncMock()
    svc.token.return_value = None

    with pytest.raises(Unauthorized):
        assert await svc.user_from_request(Request({"type": "http"})) is user
