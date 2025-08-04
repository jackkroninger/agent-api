from langchain_core.tools import tool
from pydantic import BaseModel, Field
from googleapiclient.discovery import build, Resource
from google.oauth2.credentials import Credentials
from utils import google
from utils.errors import GoogleOauthFaliure
from typing import Optional
from langchain_core.runnables import RunnableConfig
from googleapiclient.http import HttpRequest


class ToolKit():
    def __init__(self):
        self.tools = [self.create_event, self.get_event, self.get_many_events, self.update_event, self.delete_event]

    @tool("create_event", description="Create an event on the user's calendar")
    async def create_event(
        cfg: RunnableConfig,
        summary: str = Field(description="The title of the event"),
        description: str = Field(description="The description of the event. Can contain HTML"),
        start: str = Field(description="The (inclusive) start time of the event in the format: YYYY-MM-DDThh:mm:ss"),
        end: str = Field(description="The (exclusive) end time of the event in the format: YYYY-MM-DDThh:mm:ss"),
        time_zone: str = Field(description="The time zone in which the time is specified. (Formatted as an IANA Time Zone Database name, e.g. 'America/Denver')"),
        location: str = Field(description="The geographic location of the event as free-form text"),
        ):

        user_id: str = cfg["configurable"].get("user_id")
        try:
            creds: Credentials = await google.get_google_oauth_creds(user_id)
        except GoogleOauthFaliure as e:
            return e.message
        service: Resource = build('calendar', 'v3', credentials=creds)

        body = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start,
                "timeZone": time_zone
            },
            "end": {
                "dateTime": end,
                "timeZone": time_zone
            },
            "location": location
        }
        result = service.events().insert(
            calendarId='primary', 
            body=body
        ).execute()

        return result
    

    @tool("get_event", description="Get an event from the user's calendar")
    async def get_event(
        cfg: RunnableConfig,
        event_id: str = Field(description="The ID of the event to get"),
        ):

        user_id: str = cfg["configurable"].get("user_id")
        try:
            creds: Credentials = await google.get_google_oauth_creds(user_id)
        except GoogleOauthFaliure as e:
            return e.message
        service: Resource = build('calendar', 'v3', credentials=creds)

        result = service.events().get(
            calendarId='primary',
            eventId=event_id
        ).execute()

        return result
    

    @tool("get_many_events", description="Get many events from the user's calendar")
    async def get_many_events(
        cfg: RunnableConfig,
        max_results: int = Field(description="The maximum number of events returned on one result page. The default is 250."),
        time_min: str = Field(description="Lower bound (exclusive) for an event's start time to filter by. Must be in the format: YYYY-MM-DDThh:mm:ssZtz"),
        time_max: str = Field(description="Upper bound (exclusive) for an event's start time to filter by. Must be in the format: YYYY-MM-DDThh:mm:ssZtz"),
        search_query: Optional[str] = Field(description="(Optional) Free text search terms to find events that match these terms in any field")
        ):

        user_id: str = cfg["configurable"].get("user_id")
        try:
            creds: Credentials = await google.get_google_oauth_creds(user_id)
        except GoogleOauthFaliure as e:
            return e.message
        service: Resource = build('calendar', 'v3', credentials=creds)

        result = service.events().list(
            calendarId='primary',
            maxResults=max_results,
            timeMin=time_min,
            timeMax=time_max,
            q=search_query
        ).execute()

        response_keys = ["end","htmlLink","id", "start", "summary","description"]
        items = dict(result.items())
        output_items = []
        for item in items["items"]:
            output = {}
            for k,v in item.items():
                if k in response_keys:
                    output[k] = v
            output_items.append(output)
        return output_items
    

    @tool("update_event", description="Update an event on the user's calendar. Only the fields provided will be updated, other fields will remain unchanged")
    async def update_event(
        cfg: RunnableConfig,
        event_id: str = Field(description="The ID of the event to update"),
        summary: Optional[str] = Field(description="(Optional) The title of the event"),
        description: Optional[str] = Field(description="(Optional) The description of the event. Can contain HTML"),
        start: Optional[str] = Field(description="(Optional) The (inclusive) start time of the event in the format: YYYY-MM-DDThh:mm:ss"),
        end: Optional[str] = Field(description="(Optional) The (exclusive) end time of the event in the format: YYYY-MM-DDThh:mm:ss"),
        time_zone: Optional[str] = Field(description="(Optional) The time zone in which the time is specified. (Formatted as an IANA Time Zone Database name, e.g. 'America/Denver')"),
        location: Optional[str] = Field(description="(Optional) The geographic location of the event as free-form text"),
        ):

        user_id: str = cfg["configurable"].get("user_id")
        try:
            creds: Credentials = await google.get_google_oauth_creds(user_id)
        except GoogleOauthFaliure as e:
            return e.message
        service: Resource = build('calendar', 'v3', credentials=creds)

        body = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start,
                "timeZone": time_zone
            },
            "end": {
                "dateTime": end,
                "timeZone": time_zone
            },
            "location": location
        }

        result = service.events().update(
            calendarId='primary',
            eventId=event_id,
            body=body
        ).execute()

        return result
    

    @tool("delete_event", description="Delete an event from the user's calendar")
    async def delete_event(
        cfg: RunnableConfig,
        event_id: str = Field(description="The ID of the event to delete"),
        ):

        user_id: str = cfg["configurable"].get("user_id")
        try:
            creds: Credentials = await google.get_google_oauth_creds(user_id)
        except GoogleOauthFaliure as e:
            return e.message
        service: Resource = build('calendar', 'v3', credentials=creds)

        result = service.events().delete(
            calendarId='primary',
            eventId=event_id
        ).execute()

        return result
    
tk = ToolKit()