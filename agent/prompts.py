from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import yaml
import datetime
from zoneinfo import ZoneInfo

with open("config.yml", "r") as f: config = yaml.safe_load(f)

with open(f"prompts/{config["prompts"][config["prompts"]["active"]]}") as f: sys_prompt = f.read()

location = ["Denver, Colorado", ZoneInfo("America/Denver")]


prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            sys_prompt + f"The current time in {location[0]} is {datetime.datetime.now(location[1]).strftime('%Y-%m-%d %H:%M:%S')}",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)