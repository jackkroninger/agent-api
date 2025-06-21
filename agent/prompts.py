from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import yaml

with open("config.yml", "r") as f: config = yaml.safe_load(f)

with open(f"prompts/{config["prompts"][config["prompts"]["active"]]}") as f: sys_prompt = f.read()

prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            sys_prompt
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)