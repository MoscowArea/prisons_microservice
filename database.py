import uuid
from contextlib import asynccontextmanager
from typing import Callable, AsyncContextManager, cast, AsyncGenerator

from sqlalchemy import UUID, TypeDecorator, CHAR
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

from config import Config
from dto import Form, Field, FieldType

Base = declarative_base()

class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.
    """
    impl = CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                # hexstring
                return "%.32x" % value.int

class Prison(Base):
    __tablename__ = 'prison'

    id: Mapped[str] = mapped_column(
        GUID(),
        primary_key=True,
    )
    name_ru: Mapped[str] = mapped_column(nullable=False)
    name_ua: Mapped[str] = mapped_column(nullable=False)
    subject: Mapped[str] = mapped_column()
    object_type: Mapped[str] = mapped_column(nullable=False)
    lat: Mapped[float] = mapped_column()
    lon: Mapped[float] = mapped_column()
    address: Mapped[str] = mapped_column()
    management: Mapped[str] = mapped_column()
    employees_count: Mapped[int] = mapped_column()
    prisoners_count: Mapped[int] = mapped_column()
    staff: Mapped[str] = mapped_column()
    contacts: Mapped[str] = mapped_column()

    @staticmethod
    def fields() -> list[Field]:
        return [
            Field(name="id", type=FieldType.string, required=False),
            Field(name="name_ru", type=FieldType.string),
            Field(name="name_ua", type=FieldType.string),
            Field(name="subject", type=FieldType.string),
            Field(name="object_type", type=FieldType.string),
            Field(name="lat", type=FieldType.floating),
            Field(name="lon", type=FieldType.floating),
            Field(name="address", type=FieldType.string),
            Field(name="management", type=FieldType.string),
            Field(name="employees_count", type=FieldType.integer),
            Field(name="prisoners_count", type=FieldType.integer),
            Field(name="staff", type=FieldType.string),
            Field(name="contacts", type=FieldType.string)
        ]


async def setup_database(
        config: Config,
) -> tuple[Callable[[], AsyncContextManager[AsyncSession]], AsyncEngine, Form]:
    engine = create_async_engine(
        cast(str, config.dsn),
        pool_pre_ping=True,
    )

    session_local = async_sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def session() -> AsyncGenerator[AsyncSession, None]:
        async with session_local() as session_:
            yield session_

    form = Form(
        name=config.form_name,
        description=config.description,
        fields=Prison.fields()
    )
    return asynccontextmanager(session), engine, form
