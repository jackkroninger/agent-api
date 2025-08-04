from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent

node_list = ["scheduling_agent"]

def create_prompt(system_prompt):
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                system_prompt,
            ),
            MessagesPlaceholder(
                variable_name="messages"
            )
        ]
    )

def create_agent(model_name: str, model_provider: str, temperature: float, structured_out = None, tools = []):
    model = init_chat_model(
        model=model_name, # model name
        model_provider=model_provider,
        temperature=temperature
    )
    
    # Bind tools first, before applying structured output
    if tools:
        model = model.bind_tools(tools)
    
    # Apply structured output after binding tools
    if structured_out:
        model = model.with_structured_output(structured_out)
    
    if tools:
        agent = create_react_agent(
            model,
            tools
        )
        
        return agent
    else:
        return model
