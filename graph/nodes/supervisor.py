import os, yaml
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from graph.state import State
from utils.loggers import TrainingDataLogger
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
from utils.postgres import MemoryDB
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, HumanMessage
from utils.nodes import create_prompt, create_agent, node_list
from typing import Union, Literal, Optional
from langgraph.types import Command
from graph.tools import supervisor as supervisor_tools

td_logger = TrainingDataLogger(__name__)

with open("config.yml") as f: config = yaml.safe_load(f)

NODE_CONFIG = {
    "model": "mistral-small-2506",
    "model_provider": "mistralai",
    "temperature": 0,
    "prompt": "prompts/supervisor.txt"
}

with open(NODE_CONFIG["prompt"]) as f: INSTRUCTIONS: str = f.read()

os.environ["MISTRAL_API_KEY"] = config["mistral"]["key"]

class ModelOutput(BaseModel):
    content: Optional[str] = Field(description="Response to the user or prompt to the agent")
    tool: Optional[str] = Field(description="Tool to invoke")
    agent: Optional[str] = Field(description="Agent to call")
    memory_action: Optional[str] = Field(description="Memory action to take: 'add' or 'get', followed by the query. For example: 'add: memory text' or 'get: query text'")
    

MODEL = create_agent(
    NODE_CONFIG["model"], # model name
    NODE_CONFIG["model_provider"],
    NODE_CONFIG["temperature"],
    structured_out=ModelOutput
    # tools=supervisor_tools.tool_list
    )

PROMPT = create_prompt(INSTRUCTIONS)

AGENT = create_react_agent(
    MODEL,
    []
)


async def invoke(state: State, cfg: RunnableConfig): # graph `model` node
    resp = await AGENT.ainvoke(await PROMPT.ainvoke(state))

    print(resp)
    print(dict(resp))


    td_logger.log({
        "user": dict(state["messages"][-1]),
        "ai": dict(resp["messages"][-1]),
        "thread_id": cfg["configurable"].get("thread_id"), 
        "user_id": cfg["configurable"].get("user_id")
    })
    return {"messages": [resp]}