from fastapi import FastAPI, Depends
import requests as rq
from supabase import create_client
import yaml
from gotrue.errors import AuthApiError
from fastapi.security import HTTPBearer
from typing import Literal
from pydantic import BaseModel

with open("config.yml", "r") as f: config = yaml.safe_load(f)

supabase = create_client(config["supabase"]["url"], config["supabase"]["key"])

app = FastAPI()

bearer = HTTPBearer()

class UserAuthenticationFaliure(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class InvalidParameter(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class Response(BaseModel):
    data: str | list | dict | None = None
    error: str | None = None

class Token(BaseModel):
    token: str | None = None
    error: str | None = None

def check_token(token):
    try:
        response = supabase.auth.get_user(token)
        return response
    except AuthApiError as e:
        raise UserAuthenticationFaliure("Invalid token")
    
def get_history(userID: str, num: int): # get the full chat history from Redis/N8N 
    resp = rq.get(
        url="https://n8n.k7r.dev/webhook/get-history",
        params={
            "id": userID
        }
    ) # get the raw chat history
    return_list = []
    for item in resp.json(): # convert to json and reformat
        if item["type"] == "ai":
            msg_type = "assistant" # change "ai" to "assistant"
        elif item["type"] == "human":
            msg_type = "user" # change "human" to "user"

        return_list.append({"role": msg_type, "msg": item["content"]}) # add message to return list

    return_list = list(reversed(return_list)) # reversed list (oldest messages first)

    if len(return_list) > num: # limit to num messages
        return_list = return_list[-num:]

    return return_list # return 

@app.post("/login", response_model=Token)
async def login(username: str, password: str):
    """
    Login with username and password.\n
    `username` parameter is the email of the user.\n
    `password` parameter is the plaintext password of the user.\n
    Will return: `{"token": str}`
    """
    try:
        response = supabase.auth.sign_in_with_password({"email": username,"password": password})
        return {"token": response.session.access_token}
    except AuthApiError as e:
        return {"error": str(e)}

@app.get("/master/{operation}", response_model=Response)
async def master(operation: Literal["chat", "history"], prompt: str = None, num: int = 0, token: str = Depends(bearer)):
    """
    # Master Agent Endpoint
    `/master/chat`:\n
    Chat with the master agent.\n
    `prompt` parameter is the prompt to send to the master agent.\n
    Will return: `{"response": str}`\n
    `/master/history`:\n
    Returns the user's chat history with the master agent.\n
    `num` parameter determines the number of messages to return. By default, `num` is 0. Meaning if nothing passed, function will respond with the entire chat history.\n
    Will return: `{"history":[{"role": "assistant" | "user", "msg": str}]}`
    """
    try:
        userID = check_token(token.credentials).user.id
        if operation == "chat":
            if not prompt: raise InvalidParameter("prompt is required for chat operation")
            response = rq.get(
                url="https://n8n.k7r.dev/webhook/master-agent",
                params={
                    "sessionId": str(userID),
                    "chatInput": str(prompt)
                }
            )
            return {"data": response.json()["output"]}
        elif operation == "history":
            return {"data": get_history(userID, num)}
        
    except UserAuthenticationFaliure as e:
        return {"error": e.message}
    except InvalidParameter as e:
        return {"error": e.message}