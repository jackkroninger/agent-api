from langchain_core.tools import tool
from langchain_core.messages import AIMessage
from langgraph.types import Command
from pydantic import Field
from langgraph.graph import END
from typing import Union, Literal, Optional
from utils.postgres import MemoryDB
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode

ROUTES = ["scheduling_agent"]
@tool("call_agent", description="Call an agent by passing the agent name and prompt to send to the agent")
def call_agent(
        agent: Literal["scheduling_agent"] = Field(description=f"Key of the subgraph/agent to call as a string. The options are: {', '.join(ROUTES)}"),
        prompt: str = Field(description="Prompt to send to the agent")
        ) -> Command[Literal["scheduling_agent"]]:
    
    return Command(
        update={"messages": [AIMessage(prompt)]},
        goto=agent
    )

@tool("add_memory", description="Add a memory to the long term memory database")
def add_memory(
    cfg: RunnableConfig,
    memory: str = Field(description="Memory to add to the database")
    ) -> None:

    memory_db: MemoryDB = cfg["configurable"].get("memory_db")
    memory_db.create(memory, cfg["configurable"].get("user_id"))
    
@tool("search_memories", description="Search the long term memory database")
def search_memories(
    cfg: RunnableConfig,
    query: str = Field(description="Query to search for in the database")
    ) -> list:

    memory_db: MemoryDB = cfg["configurable"].get("memory_db")
    return memory_db.search(query, cfg["configurable"].get("user_id"))

tool_list = [
    call_agent,
    add_memory,
    search_memories
]

tool_node = ToolNode(tool_list)