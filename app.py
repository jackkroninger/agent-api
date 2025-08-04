from fastapi import FastAPI, Depends, BackgroundTasks, Request, status, Response, Depends
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from gotrue.errors import AuthApiError
from fastapi.security import HTTPBearer
from utils import auth, errors, schemas
from google_auth_oauthlib.flow import InstalledAppFlow
from utils import google as gauth
from utils import postgres as pg
import json, os, yaml, asyncpg
from graph.compiler import GraphCompiler, CompiledGraph
from typing import Union, Literal
from utils.middleware import AuthMiddleware

os.makedirs('logs/', exist_ok=True)

with open("config.yml", "r") as f: config = yaml.safe_load(f)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # before
    app.state.graph = await GraphCompiler()
    yield
    # after
    await app.state.db_pool.close()

app = FastAPI(lifespan=lifespan)
app.add_middleware(AuthMiddleware)
bearer = HTTPBearer()

@app.post("/login", response_model=schemas.Token, status_code=200)
async def login(body: schemas.LoginBody, response: Response):
    """
    Login with username and password.\n
    `username` parameter is the email of the user.\n
    `password` parameter is the plaintext password of the user.\n
    Will return: `{"token": str}`
    """
    try:
        return {"token": await auth.login(body.username, body.password)}
    except AuthApiError as e:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": str(e)}

@app.post("/chat/{stream}", response_model=None) 
async def chat(
        body: schemas.ChatBody, # defined in utils/schemas
        background: BackgroundTasks, # inject background tasks to run db writes in the background
        response: Response, # inject response object to set status code
        request: Request, # inject request object to access user_id
        stream: Union[Literal["stream"], None] = None, # path parameter to enable streaming
        token: str = Depends(bearer) # secure the endpoint
    ):
    graph: CompiledGraph = request.state.graph # get graph from app state
    try:
        pg.log_chat(body.thread_id, body.prompt, "user", request.state.user_id)

        if stream:
            ai_msg_buffer = []
            async def event_generator():
                async for piece in graph.chat(msg=body.prompt, thread_id=body.thread_id, user_id=request.state.user_id, stream=True): 
                    ai_msg_buffer.append(piece) # collect for logging
                    yield piece  

                background.add_task(pg.log_chat, body.thread_id, "".join(ai_msg_buffer), "ai", request.state.user_id) # log ai chat
            
            return StreamingResponse(event_generator(), media_type="text/event-stream")
        else:
            resp = await graph.chat(msg=body.prompt, thread_id=body.thread_id, user_id=request.state.user_id)
            background.add_task(pg.log_chat, body.thread_id, resp, "ai", request.state.user_id)
            return {"data": resp}
    except errors.UserAuthenticationFaliure as e:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": e.message}
    except errors.InvalidParameter as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": e.message}
    
@app.get("/history", response_model=schemas.Response)
async def history(thread_id: str, response: Response, request: Request, token: str = Depends(bearer), num: int = 0):
    try:
        return {"data": await pg.get_chat(thread_id, request.state.user_id, num)}
    
    except errors.UserAuthenticationFaliure as e:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": e.message}
    
@app.get("/oauth2callback", response_model=schemas.Response)
async def oauth2callback(request: Request, oauth_flow: InstalledAppFlow = Depends(gauth.get_oauth_flow)):
    code = request.query_params["code"]
    oauth_flow.fetch_token(code=code)
    await gauth.update_oath_token(app, json.dumps({"token":f"{request.query_params["state"]}"}), oauth_flow.credentials.to_json(), True)
    # print(app.state.google_oauth_flow.credentials.to_json())
    return {
        "data": "Credentials updated successfully"
    }
