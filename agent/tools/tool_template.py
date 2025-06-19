from langchain_core.tools import tool
from pydantic import BaseModel, Field

class ToolInputSchema(BaseModel):
    """Description_of_Tool"""
    param: type = Field(description="Param_Description")

@tool("tool_name", args_schema=ToolInputSchema)
def tool(param: type) -> type:
    return param