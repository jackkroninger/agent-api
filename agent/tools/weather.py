from langchain_core.tools import tool
from pydantic import BaseModel, Field

class ToolInputSchema(BaseModel):
    """Get the weather in a city"""
    city: str = Field(description="Name of the city. Either 'NYC' or 'LA'")

@tool("get_weather", args_schema=ToolInputSchema)
def get_weather(city: str) -> str:
    if city == 'NYC':
        return "Sunny"
    elif city == 'LA':
        return "Cloudy"
    else:
        return "Unknown"