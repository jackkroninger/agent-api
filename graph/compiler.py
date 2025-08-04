from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import START, StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.state import CompiledStateGraph
from graph.state import State
from graph.nodes import supervisor, scheduling_agent, evaluator
from graph.tools import scheduling_agent as sa_tools
from graph.tools import supervisor as sup_tools
import os, yaml
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage
from typing import Literal
from fastapi import Depends
from utils import postgres as pg

with open("config.yml") as f: config = yaml.safe_load(f)

class CompiledGraph(BaseModel):
    graph: CompiledStateGraph

    class Config:
        arbitrary_types_allowed = True

    async def chat(self, msg: str, thread_id: str, user_id: str, stream: bool = False, memory_db: pg.MemoryDB = Depends(pg.MemoryDB), user_db: pg.Session = Depends(pg.get_async_session)):
        cfg = {
            "configurable": {
                "thread_id": thread_id, 
                "user_id": user_id,
                "memory_db": memory_db,
                "user_db": user_db
            }
        }
        if stream:
            async for chunk, metadata in self.graph.astream( # iterate over chunks streamed from model
                    {"messages": [HumanMessage(msg)], "language": "English"}, # pass user input to model
                    cfg, # pass config to model
                    stream_mode="messages",

                    ):
                
                if isinstance(chunk, AIMessage): # if chunk is an AIMessage (not human message)
                    yield chunk.content
        else:
            yield await self.graph.ainvoke(
                {"messages": [HumanMessage(msg)], "language": "English"}, # pass user input to model
                cfg
            )


async def GraphCompiler(checkpoint: Literal["langsmith", None] = None) -> CompiledGraph:
    graph = StateGraph(state_schema=State)
    if not checkpoint:
        checkpointer = AsyncPostgresSaver(config["postgres"]["uri"],)
        checkpointer.setup()

    """ Create Nodes"""
    graph.add_node("supervisor", supervisor.invoke) # create supervisor node
    graph.add_node("scheduling_agent", scheduling_agent.invoke) # create scheduling agent node
    # graph.add_node("scheduling_agent_tools", ToolNode(sa_tools.tk.tools))
    graph.add_node("supervisor_tools", sup_tools.tool_node)


    """ Create Edges """
    graph.add_edge(START, "supervisor") # add connection from start to supervisor
    # graph.add_conditional_edges("router", lambda state: state["route"]) # add connection from router to next node

    # graph.add_conditional_edges("scheduling_agent", tools_condition, {END: "evaluator"})
    # graph.add_edge("scheduling_agent_tools", "scheduling_agent")

    if checkpoint:
        return CompiledGraph(
            graph=graph.compile()
        )
    return CompiledGraph(
        graph=graph.compile(checkpointer=checkpointer)
    )
        