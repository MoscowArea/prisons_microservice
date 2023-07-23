import uuid
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from database import Prison
from dto import Form
from presentation.dependencies import form_scope, db_session_scope

router = APIRouter()


@router.get("/")
async def get_all_data(session: Annotated[AsyncSession, Depends(db_session_scope)]):
    return (await session.execute(
        select(Prison)
    )).fetchall()


@router.get("/scheme")
async def get_scheme(form: Annotated[Form, Depends(form_scope)]):
    return form


@router.get("/")
async def get_data_by_id(data_id: uuid.UUID, session: Annotated[AsyncSession, Depends(db_session_scope)]):
    data = await session.get(Prison, data_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return data


@router.put("/")
async def create_data(data: dict[str, Any]):
    pass
