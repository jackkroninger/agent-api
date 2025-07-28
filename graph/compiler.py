from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import START, StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from graph.state import State
from graph import tools, nodes
import os, yaml

with open("config.yml") as f: config = yaml.safe_load(f)

class GraphCompiler:
    async def __init__(self):
        self.graph = StateGraph(state_schema=State)
        checkpointer = AsyncPostgresSaver(config["postgres"]["url"],)
        checkpointer.setup()

        """ Create Nodes"""
        self.graph.add_node("router", nodes.router.invoke) # create router node

        self.graph.add_node("scheduling_agent", nodes.scheduling_agent.invoke) # create scheduling agent node
        self.graph.add_node("scheduling_agent_tools", ToolNode(tools.scheduling_agent.TOOLS))

        self.graph.add_node("research_agent", nodes.research_agent.invoke) # create scheduling agent node
        self.graph.add_node("research_agent_tools", ToolNode(tools.research_agent.TOOLS))

        self.graph.add_node("it_agent", nodes.it_agent.invoke) # create scheduling agent node
        self.graph.add_node("it_agent_tools", ToolNode(tools.it_agent.TOOLS))

        self.graph.add_node("dev_agent", nodes.dev_agent.invoke) # create scheduling agent node
        self.graph.add_node("dev_agent_tools", ToolNode(tools.dev_agent.TOOLS))

        self.graph.add_node("evaluator", nodes.evaluator.invoke) # create evaluator node

        """ Create Edges """
        self.graph.add_edge(START, "router") # add connection from start to router
        self.graph.add_conditional_edges("router", lambda state: state["route"]) # add connection from router to next node

        self.graph.add_conditional_edges("scheduling_agent", tools_condition, {END: "evaluator"})
        self.graph.add_edge("scheduling_agent_tools", "scheduling_agent")

        self.graph.add_conditional_edges("research_agent", tools_condition, {END: "evaluator"})
        self.graph.add_edge("research_agent_tools", "research_agent")

        self.graph.add_conditional_edges("it_agent", tools_condition, {END: "evaluator"})
        self.graph.add_edge("it_agent_tools", "it_agent")

        self.graph.add_conditional_edges("dev_agent", tools_condition, {END: "evaluator"})
        self.graph.add_edge("dev_agent_tools", "dev_agent")

        self.graph.add_conditional_edges("evaluator", lambda state: state["route"]) # either "END" or "router"
