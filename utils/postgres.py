
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB
import uuid
from sqlalchemy import Column
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime
from sqlmodel import Field, SQLModel
import yaml, asyncio
from fastapi import Depends
from argon2 import PasswordHasher

with open("config.yml", "r") as f: config = yaml.safe_load(f)

async_engine = create_async_engine(
    config["postgres"]["uri"],
    echo=True,
    future=True
)

async def get_async_session():
   async_session = sessionmaker(
       bind=async_engine, class_=AsyncSession, expire_on_commit=False
   )
   async with async_session() as session:
       yield session

class chat_history(SQLModel, table=True):
    id: Optional[str] | None = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user: str = Field(foreign_key="user.id")
    thread_id: str
    role: str
    content: str
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True),server_default=func.now(),nullable=False))

class User(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    email: str
    password: str
    gcp_creds: Optional[dict] = Field(sa_column=Column(JSONB,nullable=True),default_factory=dict)
    refresh_token: Optional[str]

async def db_setup():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

asyncio.run(db_setup())

async def create_user(
        name: str,
        email: str,
        password: str,
        db: AsyncSession = Depends(get_async_session)
):
    hashed_password = 
    