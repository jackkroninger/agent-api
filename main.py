from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import requests as rq
import yaml
from gotrue.errors import AuthApiError
from fastapi.security import HTTPBearer
from agent import graph, db
from langgraph.checkpoint.redis import AsyncRedisSaver
from utils import auth, errors, schemas
import asyncpg

with open("config.yml", "r") as f: config = yaml.safe_load(f)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # before
    checkpointer = AsyncRedisSaver(config["redis"]["url"])
    await checkpointer.asetup()
    app.state.graph = graph.workflow.compile(checkpointer=checkpointer) # compile graph w/ redis memory
    app.state.db_pool = await asyncpg.create_pool(config["postgres"]["url"], min_size=5, max_size=20)
    # async with app.state.db_pool.acquire() as conn:
    #     app.state.insert_chat = await conn.prepare(
    #         """
    #         INSERT INTO chat_history(thread_id, role, content, created_at)
    #         VALUES ($1, 'user', $2, $3),
    #                ($1, 'ai',   $4, $5)
    #         """
    #     )
    yield
    # after
    await app.state.db_pool.close()

app = FastAPI(lifespan=lifespan)
bearer = HTTPBearer()
    
# def get_history(userID: str, num: int): # get the full chat history from Redis/N8N 
#     resp = rq.get(
#         url="https://n8n.k7r.dev/webhook/get-history",
#         params={
#             "id": userID
#         }
#     ) # get the raw chat history
#     return_list = []
#     for item in resp.json(): # convert to json and reformat
#         if item["type"] == "ai":
#             msg_type = "assistant" # change "ai" to "assistant"
#         elif item["type"] == "human":
#             msg_type = "user" # change "human" to "user"

#         return_list.append({"role": msg_type, "msg": item["content"]}) # add message to return list

#     return_list = list(reversed(return_list)) # reversed list (oldest messages first)

#     if len(return_list) > num: # limit to num messages
#         return_list = return_list[-num:]

#     return return_list # return 

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
async def chat(prompt: str, background: BackgroundTasks, token: str = Depends(bearer)):
    input_time = await app.state.db_pool.fetchval("SELECT NOW()")
    try:
        userID = auth.check_token(token.credentials).user.id

        userID = "0011"

        ai_msg_buffer = []

        async def event_generator():
            async for piece in graph.chat(prompt, str(userID), app):
                ai_msg_buffer.append(piece)         # collect for later
                yield piece  

            # log input chat
            background.add_task(
                db.log_chat,
                app,
                userID,
                prompt,
                "".join(ai_msg_buffer),
                input_time
            )
        
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
        return {"data": await db.get_chat(app, userID, num)}
    
    except errors.UserAuthenticationFaliure as e:
        return {"error": e.message}
    
# TODO infrustructure is done. Chat msgs are logged after request processes, retrival is working
# TODO add prompt templating to agent to better structure system prompts
# TODO finish following tutorial for basic chatbot functionality