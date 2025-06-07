import asyncio
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.redis import AsyncRedisSaver
from langgraph.graph import START, MessagesState, StateGraph, END
import os, yaml
from fastapi import FastAPI

with open("config.yml") as f: config = yaml.safe_load(f)

os.environ["GOOGLE_API_KEY"] = config["google"]["key"]

model = init_chat_model(
    "gemini-2.5-flash-preview-05-20", # model name
    model_provider="google_genai" 
    )

async def call_model(state: MessagesState): # graph `model` node
    return {"messages": await model.ainvoke(state["messages"])} # async invoke model

workflow = StateGraph(state_schema=MessagesState) # create graph
workflow.add_edge(START, "model") # add connection from start to model
workflow.add_node("model", call_model) # create model node
workflow.add_edge("model", END) # add connection from model to end

# async def build():
#     memory = AsyncRedisSaver(config["redis"]["url"]) # create redis saver for chat history

#     global graph
#     graph = workflow.compile(checkpointer=memory) # compile graph

# asyncio.run(build())

async def chat(msg: str, _id: str, app: FastAPI): 
    async for chunk, metadata in app.state.graph.astream( # iterate over chunks streamed from model
            {"messages": [HumanMessage(msg)], "language": "English"}, # pass user input to model
            {"configurable": {"thread_id": _id}}, # pass config to model
            stream_mode="messages"
            ):
        if isinstance(chunk, AIMessage): # if chunk is an AIMessage (not human message)
            yield chunk.content