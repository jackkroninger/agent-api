from langchain_core.tools import tool
from pydantic import BaseModel, Field
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from fastapi import FastAPI
from utils import auth
from utils.errors import GoogleOauthFaliure

class ToolInputSchema(BaseModel):
    """Description_of_Tool"""
    param: type = Field(description="Param_Description")

@tool("google_calendar", args_schema=ToolInputSchema)
def google_calendar(param: type) -> type:
    return param

async def cal_test(app: FastAPI, user_id: str):
    creds, status = await auth.get_google_oauth_creds(app, user_id)
    if not status: raise GoogleOauthFaliure(f"please sign in by following the link: {creds}")

    service =  build('calendar', 'v3', credentials=creds)
    events_result = service.events().list(
        calendarId='primary',
        maxResults=20,
        singleEvents=True,
        orderBy='startTime',
        timeMin="2025-06-01T00:00:00-07:00"
    ).execute().get('items', [])
    output_ls = []
    for event in events_result:
        start = event['start'].get('dateTime', event['start'].get('date'))
        output_ls.append(f"{start} - {event['summary']}")
    return output_ls