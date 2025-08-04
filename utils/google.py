from fastapi import FastAPI
# from utils.database import write_oath_token, get_oath_token, update_oath_token
from google.auth.transport.requests import Request
import json, yaml
from utils.errors import GoogleOauthFaliure
import utils.postgres as pg
from sqlmodel import Field, SQLModel, select
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

with open("config.yml", "r") as f: config = yaml.safe_load(f)

async def get_oauth_flow():
    with InstalledAppFlow.from_client_secrets_file(
        client_secrets_file=config["google"]["oauth2_credentials"], 
        scopes=config["google"]["oauth2_scopes"], 
        redirect_uri=config["google"]["redirect_uri"]
            ) as flow:
        
        yield flow

async def write_oath_token(user_id: str, creds: str, refresh_token: str | None = None, db: AsyncSession = Depends(pg.get_async_session)) -> None:
    STATEMENT = select(pg.User).where(pg.User.id == user_id)
    user = await db.exec(STATEMENT).first()
    if not user: raise GoogleOauthFaliure("User not found")
    if refresh_token: user.refresh_token = refresh_token
    user.gcp_creds = creds
    db.add(user)
    await db.commit()

async def update_oath_token(user_id: str, creds: str, verification: bool = False, db: AsyncSession = Depends(pg.get_async_session)) -> None:
    if not verification: # not using callback token, Updating by user ID
        STATEMENT = select(pg.User).where(pg.User.id == user_id)
    else: # Using callback token, updating by creds
        STATEMENT = select(pg.User).where(pg.User.gcp_creds == user_id)

    user = await db.exec(STATEMENT).first()
    if not user: raise GoogleOauthFaliure("User not found")
    user.gcp_creds = creds
    if "refresh_token" in creds: user.refresh_token = creds["refresh_token"]
    db.add(user)
    await db.commit()


async def get_oath_token(user_id: str, db: AsyncSession = Depends(pg.get_async_session)):
    STATEMENT = select(pg.User).where(pg.User.id == user_id)
    user = await db.exec(STATEMENT).first()
    if not user: raise GoogleOauthFaliure("User not found")

    creds = user.gcp_creds
    ref_token = user.refresh_token

    if isinstance(creds, str):
        creds = json.loads(creds)

    if "refresh_token" not in creds:
        creds["refresh_token"] = ref_token

    return Credentials.from_authorized_user_info(
        creds,
        scopes=config["google"]["oauth2_scopes"]
    )

def generate_auth_url(oauth_flow: InstalledAppFlow = Depends(get_oauth_flow)):
    return oauth_flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user.
        access_type='offline',
        prompt='consent'
        )

async def get_google_oauth_creds(user_id: str, oauth_flow: InstalledAppFlow = Depends(get_oauth_flow)):
    creds = await get_oath_token(user_id)
    if creds and creds.valid:
        return creds
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            await update_oath_token(user_id, creds.to_json())
            return creds
        else:
            auth_url, callbacktoken = generate_auth_url()
            if not await get_oath_token(user_id):
                await write_oath_token(user_id, json.dumps({"token":f"{callbacktoken}"}))
            else:
                await update_oath_token(user_id, json.dumps({"token":f"{callbacktoken}"}))
            raise GoogleOauthFaliure(f"The user's Google Oauth credentials expired. Please instruct the user to sign in using the following link and retry the request: {auth_url}")