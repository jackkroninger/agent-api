from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB
import uuid
from sqlalchemy import Column
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime
from sqlmodel import Field, SQLModel, select
import yaml, asyncio
from fastapi import Depends
from argon2 import PasswordHasher
from langchain_postgres import PGVector
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document


with open("config.yml", "r") as f: config = yaml.safe_load(f)

ph = PasswordHasher()

async_engine = create_async_engine(
    config["postgres"]["uri"],
    echo=True,
    future=True
)

class MemoryDB():
    db = PGVector(
        embeddings=OllamaEmbeddings(model="nomic-embed-text"),
        collection_name="memories",
        connection=config["postgres"]["non_async_uri"],
        use_jsonb=True
    )
    # def __init__(self):
    #     self.db = PGVector(
    #         embeddings=OllamaEmbeddings(model="nomic-embed-text"),
    #         collection_name="memories",
    #         connection=config["postgres"]["non_async_uri"],
    #         use_jsonb=True
    #     )

    def __init__(self):
        pass

    def create(content: str, user_id: str):
        MemoryDB.db.add_documents(
            [Document(page_content=content, metadata={"user_id": user_id})],
            ids=[str(uuid.uuid4())]
        )

    def delete(id: str):
        MemoryDB.db.delete(ids=[id])

    def search(query: str, user_id: str, k: int = 3):
        return MemoryDB.db.similarity_search(query, k=k, filter={"user_id": {"$eq": user_id}})
    

async def get_async_session():
   async_session = sessionmaker(
       bind=async_engine, class_=AsyncSession, expire_on_commit=False
   )
   async with async_session() as session:
       yield session

class Chat_History(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user: str = Field(foreign_key="user.id")
    thread_id: str
    role: str
    content: str
    created_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True),server_default=func.now(),nullable=False))

class User(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    email: str
    password: str
    location: Optional[str]
    timezone: Optional[str]
    gcp_creds: Optional[dict] = Field(sa_column=Column(JSONB,nullable=True),default_factory=dict)
    refresh_token: Optional[str]

async def db_setup():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

# asyncio.run(db_setup())

async def create_user(
        name: str,
        email: str,
        password: str,
        db: AsyncSession = Depends(get_async_session)
    ) -> User:
    
    hashed_password = ph.hash(password)

    user = User(name=name, email=email, password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user

async def log_chat(
        thread_id: str, 
        msg: str,
        role: str,
        user_id: str,
        db: AsyncSession = Depends(get_async_session)
) -> None:

    chat_msg = Chat_History(thread_id=thread_id, user=user_id, role=role, content=msg)
    db.add(chat_msg)
    await db.commit()

async def get_chat(
        thread_id: str, 
        user_id: str,
        num: int = 0,
        db: AsyncSession = Depends(get_async_session)
) -> list:

    if num > 0:
        STATEMENT = select(Chat_History).where(Chat_History.thread_id == thread_id and Chat_History.user == user_id).order_by(Chat_History.created_at.desc()).limit(num)
        return await db.exec(STATEMENT).all()
    else:
        STATEMENT = select(Chat_History).where(Chat_History.thread_id == thread_id and Chat_History.user == user_id).order_by(Chat_History.created_at.desc())
        return await db.exec(STATEMENT).all()