from fastapi import Request
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from dto import Form


async def db_session_scope(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.state.db_session() as session:
        yield session


async def form_scope(request: Request) -> Form:
    return request.app.state.form()
