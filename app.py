from fastapi import FastAPI, Depends, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import requests as rq
import yaml
from gotrue.errors import AuthApiError
from fastapi.security import HTTPBearer
from agent import graph
from agent.tools import google_cal
from langgraph.checkpoint.redis import AsyncRedisSaver
from utils import auth, errors, schemas, database
import asyncpg
from google_auth_oauthlib.flow import InstalledAppFlow
import json


with open("config.yml", "r") as f: config = yaml.safe_load(f)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # before
    checkpointer = AsyncRedisSaver(config["redis"]["url"])
    await checkpointer.asetup()
    app.state.graph = graph.workflow.compile(checkpointer=checkpointer) # compile graph w/ redis memory
    app.state.db_pool = await asyncpg.create_pool(config["postgres"]["url"], min_size=5, max_size=20)
    app.state.google_oauth_flow = InstalledAppFlow.from_client_secrets_file(config["google"]["oauth2_credentials"], config["google"]["oauth2_scopes"], redirect_uri=config["google"]["redirect_uri"])
    yield
    # after
    await app.state.db_pool.close()

app = FastAPI(lifespan=lifespan)
bearer = HTTPBearer()

@app.post("/login", response_model=schemas.Token)
async def login(username: str, password: str):
    """
    Login with username and password.\n
    `username` parameter is the email of the user.\n
    `password` parameter is the plaintext password of the user.\n
    Will return: `{"token": str}`
    """
    try:
        return {"token": auth.login(username, password)}
    except AuthApiError as e:
        return {"error": str(e)}

@app.get("/chat", response_model=None)
async def chat(prompt: str, thread_id: str, background: BackgroundTasks, token: str = Depends(bearer)):
    input_time = await app.state.db_pool.fetchval("SELECT NOW()")
    try:
        userID = auth.check_token(token.credentials).user.id

        # print(app.__dict__)

        ai_msg_buffer = []
        async def event_generator():
            async for piece in graph.chat(msg=prompt, _id=thread_id, app=app, user_id=userID):
                ai_msg_buffer.append(piece)         # collect for later
                yield piece  

            # log input chat
            background.add_task(database.log_chat, app, userID, prompt, "".join(ai_msg_buffer), input_time)
        
        return StreamingResponse(event_generator())
    except errors.UserAuthenticationFaliure as e:
        return {"error": e.message}
    except errors.InvalidParameter as e:
        return {"error": e.message}
    
@app.get("/history", response_model=schemas.Response)
async def history(token: str = Depends(bearer), num: int = 0):
    try:
        userID = auth.check_token(token.credentials).user.id
        userID = "0011"
        return {"data": await database.get_chat(app, userID, num)}
    
    except errors.UserAuthenticationFaliure as e:
        return {"error": e.message}
    
@app.get("/oauth2token",response_model=schemas.Response)
async def oath2token(bg: BackgroundTasks, token: str = Depends(bearer)):
    try:
        userID = auth.check_token(token.credentials).user.id
        # google_creds, status = await auth.get_google_oauth_creds(app, userID)
        service = await google_cal.cal_test(app, userID)
        return {"data": service}
    except errors.UserAuthenticationFaliure as e:
        return {"error": e.message}
    
@app.get("/oauth2callback", response_model=schemas.Response)
async def oauth2callback(request: Request):
    code = request.query_params["code"]
    app.state.google_oauth_flow.fetch_token(code=code)
    await database.update_oath_token(app, json.dumps({"token":f"{request.query_params["state"]}"}), app.state.google_oauth_flow.credentials.to_json(), True)
    # print(app.state.google_oauth_flow.credentials.to_json())
    return {
        "data": "Credentials updated successfully"
    }

    
# TODO infrustructure is done. Chat msgs are logged after request processes, retrival is working
# TODO add prompt templating to agent to better structure system prompts
# TODO finish following tutorial for basic chatbot functionality

