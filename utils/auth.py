from supabase import create_client
import yaml, jwt
from gotrue.errors import AuthApiError
from utils.errors import UserAuthenticationFaliure, JWTError
from utils.schemas import Token
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import Depends, FastAPI
from utils.postgres import get_async_session, User
from sqlmodel import select
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from datetime import datetime, timedelta


with open("config.yml", "r") as f: config = yaml.safe_load(f)

ph = PasswordHasher()


def generate_token(user_id: str) -> str:
    return str(jwt.encode(
        payload={
            "user_id": user_id,
            "exp": datetime.now() + timedelta(days=config["jwt"]["exp"])
        },
        key=config["jwt"]["secret_key"],
        algorithm=config["jwt"]["algorithm"]
    ))

def check_token(token: str) -> str:
    try:
        decoded = jwt.decode(token, config["jwt"]["secret_key"], algorithms=[config["jwt"]["algorithm"]])
        if decoded["exp"] >= datetime.now(): raise JWTError("Token expired")
        return decoded["user_id"]
    except JWTError as e:
        raise e

async def login(
        email: str,
        password: str,
        db: AsyncSession = Depends(get_async_session)
    ) -> str:

    statement = select(User).where(User.email == email)
    try:
        user = await db.exec(statement).first()

        ph.verify(user.password, password)

        return generate_token(user.id)
        
    except VerifyMismatchError:
        raise UserAuthenticationFaliure("Invalid credentials")
    # TODO catch error for user not found
