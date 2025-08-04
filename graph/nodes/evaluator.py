'''Write node that will evaluate agent response, determine if request was satisfied, if not will 
re-prompt router, if it was will format final response and respond to the user. Evaluator also has the ability to store memories.
Will work similar to memory retreval where agent writes note and invoke will see that and store it and then append the final message for the user.'''
import os, yaml
from langgraph.graph import END
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from graph.state import State
from utils.loggers import TrainingDataLogger
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
from utils.postgres import MemoryDB
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from utils.nodes import create_prompt, create_agent
from typing import Union, Literal, Optional
from langgraph.types import Command

td_logger = TrainingDataLogger(__name__)

memoriesDB = MemoryDB()

with open("config.yml") as f: config = yaml.safe_load(f)

NODE_CONFIG = {
    "model": "mistral-medium-2505",
    "model_provider": "mistralai",
    "temperature": 0,
    "prompt": "prompts/evaluator.txt"
}

with open(NODE_CONFIG["prompt"]) as f: INSTRUCTIONS: str = f.read()

os.environ["MISTRAL_API_KEY"] = config["mistral"]["key"]


class ModelOutput(BaseModel):
    route: Literal["router", END] = Field(description=f"Either 'router' or 'END'") # type: ignore
    content: str = Field(description="Response to the user or prompt to the router")
    store_memory: Optional[str] = Field(description="(Optional) Memory to store")

MODEL = create_agent(
    NODE_CONFIG["model"],
    NODE_CONFIG["model_provider"],
    NODE_CONFIG["temperature"],
    structured_out=ModelOutput
)

PROMPT = create_prompt(INSTRUCTIONS)

async def invoke(state: State, cfg: RunnableConfig) -> Command[Literal["router", END]]: # type: ignore # graph `model` node
    resp: ModelOutput = await MODEL.ainvoke(await PROMPT.ainvoke(state))

    if resp.store_memory:
        memoriesDB.create(resp.store_memory, cfg["configurable"].get("user_id"))

        

    td_logger.log({
        "node": "router",
        "user": dict(state["messages"][-1]),
        "ai": dict(resp["messages"][-1]),
        "thread_id": cfg["configurable"].get("thread_id"), 
        "user_id": cfg["configurable"].get("user_id")
    })
    return Command(
        update={"messages": [AIMessage(resp.content)]},
        goto=resp.route
    )