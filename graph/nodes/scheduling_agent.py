import os, yaml
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from graph.state import State
from utils.loggers import TrainingDataLogger
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from graph.tools.scheduling_agent import ToolKit
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from utils.nodes import create_prompt, create_agent

td_logger = TrainingDataLogger(__name__)

tk = ToolKit()

with open("config.yml") as f: config = yaml.safe_load(f)

NODE_CONFIG = {
    "model": "gemini-2.5-flash-preview-05-20",
    "model_provider": "google_genai",
    "temperature": 0,
    "prompt": "prompts/scheduling_agent.txt"
}

with open(NODE_CONFIG["prompt"]) as f: INSTRUCTIONS: str = f.read()

os.environ["GOOGLE_API_KEY"] = config["google"]["key"]

AGENT = create_agent(
    NODE_CONFIG["model"],
    NODE_CONFIG["model_provider"],
    NODE_CONFIG["temperature"],
    tools=tk.tools
)

PROMPT = create_prompt(INSTRUCTIONS)

async def invoke(state: State, cfg: RunnableConfig): # graph `model` node
    resp = await AGENT.ainvoke(await PROMPT.ainvoke(state))

    td_logger.log({
        "user": dict(state["messages"][-1]),
        "ai": dict(resp["messages"][-1]),
        "thread_id": cfg["configurable"].get("thread_id"), 
        "user_id": cfg["configurable"].get("user_id")
    })
    return {"messages": AIMessage(resp)}