from langchain_core.tools import tool
from pydantic import BaseModel, Field
from googleapiclient.discovery import build, Resource
from google.oauth2.credentials import Credentials
from fastapi import FastAPI
from utils import auth
from utils.errors import GoogleOauthFaliure
from typing_extensions import Annotated
from typing import Union
from langgraph.prebuilt import InjectedState
from utils.schemas import CreateEvent, GetEvent, UpdateEvent, DeleteEvent, GetManyEvents
from langchain_core.tools import InjectedToolArg
from langchain_core.runnables import RunnableConfig
from googleapiclient.http import HttpRequest

import pprint

class ToolInputSchema(BaseModel):
    """
Interact with the user's Google Calendar. You are able to create events, get events, update events, and delete events.
When using this tool, pass the operation (create, get, get many, update, or delete) as well as the kwargs corresponding to that operation.
Use the below examples of the kwargs for each operation.

Schema for create:
kwargs: {
    "summary": "string", (required) # Title of the event
    "description": "string", (optional) # Description of the event. Can contain HTML
    "start": (required) {
        "date": "string", (optional) # The date, in the format "yyyy-mm-dd", if this is an all-day event
        "dateTime": "string", (optional) # The time, as a combined date-time value (formatted according to RFC3339). A time zone offset is required unless a time zone is explicitly specified in timeZone
        "timeZone": "string" (optional) # The time zone in which the time is specified. (Formatted as an IANA Time Zone Database name, e.g. "Europe/Zurich".)
    },
    "end": {
        "date": "string", (optional) # The date, in the format "yyyy-mm-dd", if this is an all-day event
        "dateTime": "string", (optional) # The time, as a combined date-time value (formatted according to RFC3339). A time zone offset is required unless a time zone is explicitly specified in timeZone
        "timeZone": "string" (optional) # The time zone in which the time is specified. (Formatted as an IANA Time Zone Database name, e.g. "Europe/Zurich".)
    },
    "location": "string" (optional) # Geographic location of the event as free-form text
}

Schema for get_many:
kwargs: {
    "maxResults": "integer", (optional) # Maximum number of events returned on one result page. By default the value is 250 events
    "q": "string", (optional) # Free text search terms to find events that match these terms in any field
    "timeMax": "string", (optional) # Upper bound (exclusive) for an event's start time to filter by. Must be an RFC3339 timestamp with mandatory time zone offset, for example, 2011-06-03T10:00:00-07:00, 2011-06-03T10:00:00Z. If timeMin is set, timeMax must be greater than timeMin
    "timeMin": "string (optional) # Lower bound (exclusive) for an event's end time to filter by. Must be an RFC3339 timestamp with mandatory time zone offset, for example, 2011-06-03T10:00:00-07:00, 2011-06-03T10:00:00Z. The (exclusive) end time of the event
}

Schema for get:
kwargs: {
    "eventId": "string" # The ID of the event
}

Schema for update:
kwargs: {
    "eventId": "string", (required) # The ID of the event
    "summary": "string", (optional) # Title of the event
    "description": "string", (optional) # Description of the event. Can contain HTML
    "start": (optional) {
        "date": "string", (optional) # The date, in the format "yyyy-mm-dd", if this is an all-day event
        "dateTime": "string", (optional) # The time, as a combined date-time value (formatted according to RFC3339). A time zone offset is required unless a time zone is explicitly specified in timeZone
        "timeZone": "string" (optional) # The time zone in which the time is specified. (Formatted as an IANA Time Zone Database name, e.g. "Europe/Zurich".)
    },
    "end": (optional) {
        "date": "string", (optional) # The date, in the format "yyyy-mm-dd", if this is an all-day event
        "dateTime": "string", (optional) # The time, as a combined date-time value (formatted according to RFC3339). A time zone offset is required unless a time zone is explicitly specified in timeZone
        "timeZone": "string" (optional) # The time zone in which the time is specified. (Formatted as an IANA Time Zone Database name, e.g. "Europe/Zurich".)
    },
    location": "string" (optional) # Geographic location of the event as free-form text
}

Schema for delete:
kwargs: {
    "eventId": "string" # The ID of the event
}
    """
    action: str = Field(description="Action to perform on the calendar. Either 'create', 'get', 'get_many', 'update', or 'delete'")
    kwargs: Union[CreateEvent, GetEvent, UpdateEvent, DeleteEvent, GetManyEvents] = Field(description="Keyword arguments for the action.")

@tool("google_calendar", args_schema=ToolInputSchema)
async def tool(
    action: str, 
    kwargs: Union[CreateEvent, GetEvent, UpdateEvent, DeleteEvent, GetManyEvents], 
    config: RunnableConfig
    ) -> str:


    user_id: str = config["configurable"].get("user_id")
    app: FastAPI = config["configurable"].get("app")
    try:
        creds: Credentials = await auth.get_google_oauth_creds(app, user_id)
    except GoogleOauthFaliure as e:
        return e.message
     
    service: Resource = build('calendar', 'v3', credentials=creds)

    if action.lower() == "create":
        return await gcal_create_event(service, kwargs)
    elif action.lower() == "get":
        return await gcal_get_event(service, kwargs)
    elif action.lower() == "get_many":
        return await gcal_get_many_events(service, kwargs)
    elif action.lower() == "update":
        return await gcal_update_event(service, kwargs)
    elif action.lower() == "delete":
        return await gcal_delete_event(service, kwargs)
    else:
        return "Invalid action. Please choose one of 'create', 'get', 'get_many', 'update', or 'delete'"

async def gcal_create_event(service: Resource, kwargs: CreateEvent):
    body = {
        "colorId": None, # The color of the event. This is an ID referring to an entry in the event section of the colors definition (see the  colors endpoint).
        "summary": kwargs["summary"],
        "description": kwargs["description"],
        "location": kwargs["location"],
        "start": {
            "date": kwargs['start']['date'],
            "dateTime": kwargs['start']["dateTime"],
            "timeZone": kwargs['start']['timeZone']
        },
        "end": {
            "date": kwargs['end']['date'],
            "dateTime": kwargs['end']['dateTime'],
            "timeZone": kwargs['end']['timeZone']
        }
    }
    result = service.events().insert(
        calendarId='primary', 
        body=body
        ).execute()
    return result # TODO parse

async def gcal_get_event(service: Resource, kwargs: GetEvent):
    result = service.events().get(
        calendarId='primary',
        eventId=kwargs["eventId"]
    )
    return result # TODO parse

async def gcal_get_many_events(service: Resource, kwargs: GetManyEvents):
    result: HttpRequest = service.events().list(
        calendarId='primary',
        maxResults=kwargs["maxResults"],
        q=kwargs["q"],
        timeMax=kwargs["timeMax"],
        timeMin=kwargs["timeMin"]
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

async def gcal_update_event(service: Resource, kwargs: UpdateEvent):
    result = service.events().update(
        calendarId='primary',
        eventId=kwargs.eventId,
        body = {
            "summary": kwargs['summary'],
            "description": kwargs['description'],
            "location": kwargs['location'],
            "start": {
                "date": kwargs['start']['date'],
                "dateTime": kwargs['start']['dateTime'],
                "timeZone": kwargs['start']['timeZone']
            },
            "end": {
                "date": kwargs['end']['date'],
                "dateTime": kwargs['end']['dateTime'],
                "timeZone": kwargs['end']['timeZone']
            }
        }
    )
    return result # TODO parse

async def gcal_delete_event(service: Resource, kwargs: DeleteEvent):
    result = service.events().delete(
        calendarId='primary',
        eventId=kwargs['eventId']
    )
    return result # TODO parse



# async def cal_test(app: FastAPI, user_id: str):
#     try:
#         creds = await auth.get_google_oauth_creds(app, user_id)
#     except GoogleOauthFaliure as e:
#         return e.message

#     service =  build('calendar', 'v3', credentials=creds)
#     events_result = service.events().list(
#         calendarId='primary',
#         maxResults=20,
#         singleEvents=True,
#         orderBy='startTime',
#         timeMin="2025-06-01T00:00:00-07:00"
#     ).execute().get('items', [])
#     output_ls = []
#     for event in events_result:
#         start = event['start'].get('dateTime', event['start'].get('date'))
#         output_ls.append(f"{start} - {event['summary']}")
#     return output_ls