import os, yaml
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from graph.state import State
from utils.loggers import TrainingDataLogger
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

td_logger = TrainingDataLogger(__name__)

with open("config.yml") as f: config = yaml.safe_load(f)

NODE_CONFIG = {
    "model": "gemini-2.5-flash-preview-05-20",
    "model_provider": "google_genai",
    "temperature": 0,
    "prompt": "prompts/scheduling_agent.txt"
}

with open(NODE_CONFIG["prompt"]) as f: INSTRUCTIONS: str = f.read()

os.environ["GOOGLE_API_KEY"] = config["google"]["key"]

MODEL = init_chat_model(
    NODE_CONFIG["model"], # model name
    model_provider=NODE_CONFIG["model_provider"],
    temperature=NODE_CONFIG["temperature"]
    )

TOOLS = []

MODEL = MODEL.bind_tools(TOOLS)

AGENT = create_react_agent(
    MODEL,
    TOOLS
)

PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            INSTRUCTIONS,
        ),
        MessagesPlaceholder(
            variable_name="messages"
        )
    ]
)

async def invoke(state: State): # graph `model` node
    resp = await AGENT.ainvoke(await PROMPT.ainvoke(state))

    td_logger.log({
        "user": dict(state["messages"][-1]),
        "ai": dict(resp["messages"][-1]),
        "thread_id": state["thread_id"], 
        "user_id": state["user_id"]
    })
    return resp