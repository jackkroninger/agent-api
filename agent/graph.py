import asyncio
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables.configurable import RunnableConfig
from langgraph.checkpoint.redis import AsyncRedisSaver
from langgraph.graph import START, StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent
import os, yaml
from fastapi import FastAPI
from typing import Annotated, Union
from typing_extensions import TypedDict
from agent.tools import weather
from agent.prompts import prompt_template
from utils.loggers import TrainingDataLogger
import pprint

td_logger = TrainingDataLogger("graph")

with open("config.yml") as f: config = yaml.safe_load(f)

os.environ["GOOGLE_API_KEY"] = config["google"]["key"]

model = init_chat_model(
    "gemini-2.5-flash-preview-05-20", # model name
    model_provider="google_genai",
    temperature=0
    )

tools = [weather.get_weather]

model = model.bind_tools(tools)

agent = create_react_agent(
    model,
    tools
)

class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]
    user_id: str
    thread_id: str
    app: FastAPI | None

async def call_agent(state: State): # graph `model` node
    prompt = await prompt_template.ainvoke(state)
    resp = await agent.ainvoke(prompt)

    td_logger.log({
        "user": dict(state["messages"][-1]),
        "ai": dict(resp["messages"][-1]),
        "thread_id": state["thread_id"], 
        "user_id": state["user_id"]
    })
    return resp


workflow = StateGraph(state_schema=State) # create graph
workflow.add_node("model", call_agent) # create agent node
workflow.add_node("tools", ToolNode(tools)) # create tools node
workflow.add_conditional_edges("model", tools_condition) 
workflow.add_edge("tools", "model")
workflow.add_edge(START, "model") # add connection from start to model

async def chat(msg: str, _id: str, app: Union[FastAPI, CompiledStateGraph], user_id: str = None): 
    cfig = {"configurable": {"thread_id": _id}}
    if type(app) == FastAPI: 
        await app.state.graph.aupdate_state(cfig,values={"user_id": user_id, "thread_id": _id, "app": app})
        async for chunk, metadata in app.state.graph.astream( # iterate over chunks streamed from model
                {"messages": [HumanMessage(msg)], "language": "English"}, # pass user input to model
                cfig, # pass config to model
                stream_mode="messages"
                ):
            if isinstance(chunk, AIMessage): # if chunk is an AIMessage (not human message)
                yield chunk.content
    elif type(app) == CompiledStateGraph:
        graph = app
        await graph.aupdate_state(cfig,values={"user_id": user_id, "thread_id": _id, "app": None})
        async for chunk, metadata in graph.astream( # iterate over chunks streamed from model
                {"messages": [HumanMessage(msg)], "language": "English"}, # pass user input to model
                cfig, # pass config to model
                stream_mode="messages"
                ):
            if isinstance(chunk, AIMessage): # if chunk is an AIMessage (not human message)
                yield chunk.content
