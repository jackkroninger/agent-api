from supabase import create_client
import yaml
from gotrue.errors import AuthApiError
from utils.errors import UserAuthenticationFaliure, GoogleOauthFaliure
from utils.schemas import Token
from utils.database import write_oath_token, get_oath_token, update_oath_token
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os.path
import pickle
from fastapi import FastAPI
import json


with open("config.yml", "r") as f: config = yaml.safe_load(f)

supabase = create_client(config["supabase"]["url"], config["supabase"]["key"])

def check_token(token): # supabase
    try:
        response = supabase.auth.get_user(token)
        return response
    except AuthApiError as e:
        raise UserAuthenticationFaliure("Invalid token")
    
def login(username: str, password: str) -> str: # supabase
    try:
        response = supabase.auth.sign_in_with_password({"email": username,"password": password})
        return response.session.access_token
    except AuthApiError as e:
        raise e

def generate_auth_url(app: FastAPI):
    return app.state.google_oauth_flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user.
        access_type='offline',
        # prompt='consent'
        )
async def get_google_oauth_creds(app: FastAPI, user_id: str):
    creds = await get_oath_token(app, user_id)
    if creds and creds.valid:
        return creds
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            await update_oath_token(app, user_id, creds.to_json())
            return creds
        else:
            auth_url, callbacktoken = generate_auth_url(app)
            if not get_oath_token(app, user_id):
                await write_oath_token(app, user_id, json.dumps({"token":f"{callbacktoken}"}))
            else:
                await update_oath_token(app, user_id, json.dumps({"token":f"{callbacktoken}"}))
            raise GoogleOauthFaliure(f"The user's Google Oauth credentials expired. Please instruct the user to sign in using the following link and retry the request: {auth_url}")