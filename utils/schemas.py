from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from typing import Optional, Annotated
import json
import pprint


class Response(BaseModel):
    data: str | list | dict | None = None
    error: str | None = None

class Token(BaseModel):
    token: str | None = None
    error: str | None = None

"""GOOGLE CALENDAR TOOL SCHEMAS"""

class TimeBlock(TypedDict):
    """Input schema for a time object"""
    date: Optional[Annotated[str, 'The date, in the format "yyyy-mm-dd", if this is an all-day event.']]
    dateTime: Optional[Annotated[str, 'The time, as a combined date-time value (formatted according to RFC3339). A time zone offset is required unless a time zone is explicitly specified in timeZone.']]
    timeZone: Optional[Annotated[str, 'The time zone in which the time is specified. (Formatted as an IANA Time Zone Database name, e.g. "Europe/Zurich".)']]

class CreateEvent(TypedDict):
    """Input schema for creating an event"""
    summary: Annotated[str, 'Title of the event']
    description: Optional[Annotated[str, 'Description of the event. Can contain HTML']] 
    start: Annotated[TimeBlock, 'The (inclusive) start time of the event']
    end: Annotated[TimeBlock, 'The (exclusive) end time of the event.']
    location: Optional[Annotated[str, 'Geographic location of the event as free-form text']]

class GetManyEvents(TypedDict):
    """Input schema for getting many events"""
    maxResults: Optional[Annotated[int, 'The maximum number of events returned on one result page. The default is 250.']]
    q: Optional[Annotated[str, 'Free text search terms to find events that match these terms in any field']]
    timeMax: Optional[Annotated[str, "Upper bound (exclusive) for an event's start time to filter by. Must be an RFC3339 timestamp with mandatory time zone offset, for example, 2011-06-03T10:00:00-07:00, 2011-06-03T10:00:00Z. If timeMin is set, timeMax must be greater than timeMin"]]
    timeMin: Optional[Annotated[str, "Lower bound (exclusive) for an event's end time to filter by. Must be an RFC3339 timestamp with mandatory time zone offset, for example, 2011-06-03T10:00:00-07:00, 2011-06-03T10:00:00Z. The (exclusive) end time of the event."]]

class GetEvent(TypedDict):
    """Input schema for getting an event"""
    eventId: Annotated[str, 'The ID of the event']

class UpdateEvent(TypedDict):
    """Input schema for updating an event"""
    eventId: Annotated[str, 'The ID of the event']
    summary: Optional[Annotated[str, 'Title of the event']]
    description: Optional[Annotated[str, 'Description of the event. Can contain HTML']] 
    start: Optional[Annotated[TimeBlock, 'The (inclusive) start time of the event']]
    end: Optional[Annotated[TimeBlock, 'The (exclusive) end time of the event.']]
    location: Optional[Annotated[str, 'Geographic location of the event as free-form text']]

class DeleteEvent(TypedDict):
    """Input schema for deleting an event"""
    # eventId: str = Field(description="The ID of the event")
    eventId: Annotated[str, 'The ID of the event']

# def rep_schema():
#     # test1 = str(TimeBlock.__annotations__).replace("typing.Annotated[","").replace("typing.Optional[","[Optional, ").replace("[[","[").replace("]]","]")
#     objects = {"TimeBlock": TimeBlock, "create": CreateEvent, "get_many": GetManyEvents, "get": GetEvent, "update": UpdateEvent, "delete": DeleteEvent} #{" GetEvent, UpdateEvent, DeleteEvent}
#     finished_items = []
#     for k,v in objects.items():
#         # item = str(v.__annotations__).replace("typing.Annotated[","[").replace("typing.Optional[","[Optional, ").replace("[[","[").replace("]]","]]")
#         annotations = v.__annotations__
#         for k2,v2 in annotations.items():
#             new_value = str(v2)
#             new_value = new_value.replace(
#                 "typing.Optional[", 
#                 "[Optional, "
#             )
#             new_value = new_value.replace(
#                 "typing.Annotated[",
#                 "[Required, "
#             )
#             new_value = new_value.replace(
#                 "[Optional, [Required, ",
#                 "[Optional, "
#             )
#             new_value = new_value.replace(
#                 "]]",
#                 "]"
#             )
#             new_value = new_value.replace(
#                 "\n",
#                 ""
#             )
#             annotations[k2] = (new_value)
#         if k == "TimeBlock":
#             tb = annotations
#             # print(tb)
#         else:
#             finished_items.append( {k: annotations} )
#     # pprint.pprint(finished_items)
#     for item in finished_items:
#         for k,v in item.items():
#             for k2,v2 in v.items():
#                 new_value = str(v2)
#                 new_value = new_value.replace(
#                     "utils.schemas.TimeBlock",
#                     f"dict({tb})"
#                 )
#                 new_value = new_value.replace(
#                     "\\",
#                     ""
#                 )
#                 v[k2] = new_value

#     return finished_items

# pprint.pprint(rep_schema())
# # rep_schema()
