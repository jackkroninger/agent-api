from fastapi import FastAPI
import yaml, os, json
from redis.asyncio import Redis
from google.oauth2.credentials import Credentials
import pprint
import requests as rq

with open("config.yml", "r") as f: config = yaml.safe_load(f)

async def log_chat(
        app: FastAPI, 
        thread_id: str, 
        user_msg: str, 
        ai_msg: str, 
        input_time: str,):
    
    CHAT_SQL = """
INSERT INTO chat_history(thread_id, role, content, created_at)
VALUES ($1, 'user', $2, $3),
        ($1, 'ai',   $4, $5)
"""
    async with app.state.db_pool.acquire() as conn:
        await conn.execute(
            CHAT_SQL,
            thread_id, # thread_id
            user_msg, # content (user)
            input_time, # created_at (user)
            ai_msg, # content (ai)
            await app.state.db_pool.fetchval("SELECT NOW()") # created_at (ai)
        )

async def get_chat(app: FastAPI, thread_id: str, num: int = 0):
    async with app.state.db_pool.acquire() as conn:
        if num > 0:
            # Fetch the most recent `num`, then reverse for oldest-first
            rows = await conn.fetch(
                """
                SELECT role AS type, content, created_at AS timestamp
                FROM chat_history
                WHERE thread_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                thread_id, num,
            )
            rows = rows[::-1]
        else:
            # Fetch all messages in chronological order
            rows = await conn.fetch(
                """
                SELECT role AS type, content, created_at AS timestamp
                FROM chat_history
                WHERE thread_id = $1
                ORDER BY created_at ASC
                """,
                thread_id,
            )
    return [{"type": row["type"], "content": row["content"], "timestamp": row["timestamp"]} for row in rows]

async def write_oath_token(app: FastAPI, user_id: str, token: str):
    SQL_EXP = """
INSERT INTO gcp_oauth("user", creds)
VALUES ($1, $2)
"""
    async with app.state.db_pool.acquire() as conn:
        await conn.execute(SQL_EXP, user_id, token)

async def update_oath_token(app: FastAPI, user_id: str, token: str, verification_token: bool = False):
    token_json = json.loads(token)
    if not verification_token:
        SQL_EXP = """
UPDATE gcp_oauth
SET creds = $2
WHERE "user" = $1
    """
        async with app.state.db_pool.acquire() as conn:
            await conn.execute(SQL_EXP, user_id, token)
    else:
        if "refresh_token" not in token:
            SQL_EXP = """UPDATE gcp_oauth
SET creds = $2
WHERE creds = $1"""
            async with app.state.db_pool.acquire() as conn:
                await conn.execute(SQL_EXP, user_id, token)
        else:
            SQL_EXP = """UPDATE gcp_oauth
SET refresh_token = $3,
    creds = $2
WHERE creds = $1"""
            async with app.state.db_pool.acquire() as conn:
                await conn.execute(SQL_EXP, user_id, token, token_json["refresh_token"])

async def get_oath_token(app: FastAPI, user_id: str) -> Credentials:
    SQL_EXP = """
SELECT creds, refresh_token
FROM gcp_oauth
WHERE "user" = $1
"""
    
    async with app.state.db_pool.acquire() as conn:
        row = await conn.fetchrow(SQL_EXP, user_id)
        if not row: return

        creds = row["creds"]
        refresh_token = row["refresh_token"]
        
        if isinstance(creds, str):
            creds = json.loads(creds)

        if "refresh_token" not in creds:
            creds["refresh_token"] = refresh_token

        return Credentials.from_authorized_user_info(
            creds,
            scopes=config["google"]["oauth2_scopes"]
        )
    
'''Redis'''

rds = Redis.from_url(config["redis"]["url"], decode_responses=True)

class Redis:
    async def set_credentials(self,user_id: str, creds, ex: int = None) -> bool:
        """
        Create or replace the credentials JSON for a given user.
        :param user_id: identifier for the user
        :param creds: a JSON-serializable dict of credential info
        :param ex: optional expiry in seconds
        :return: True if the key was set
        """
        payload = json.dumps(creds)
        return await rds.set(user_id, payload, ex=ex)

    async def get_credentials(self,user_id: str):
        """
        Retrieve the stored credentials for a user, if any.
        :param user_id: identifier for the user
        :return: parsed JSON dict or None if not found or invalid
        """
        raw = await rds.get(user_id)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            await self.delete_credentials(user_id)
            return None
    
    async def update_credentials(self,user_id: str, delta: dict) -> bool:
        """
        Atomically merge and update only certain fields in the stored creds.
        :param user_id: identifier for the user
        :param delta: partial dict to merge into existing creds
        :return: True if update succeeded
        """
        async with rds.pipeline() as pipe:
            await pipe.get(user_id)
            existing_raw = await pipe.execute()
            if not existing_raw or existing_raw[0] is None:
                return False
            try:
                existing = json.loads(existing_raw[0])
            except json.JSONDecodeError:
                return False
            existing.update(delta)
            await pipe.set(user_id, json.dumps(existing))
            await pipe.execute()
            return True

    async def delete_credentials(self,user_id: str) -> int:
        """
        Remove credentials for a given user ID.
        :param user_id: identifier for the user
        :return: number of keys removed (0 or 1)
        """
        return await rds.delete(user_id)

    async def list_all_users(self,pattern: str = "*"):
        """
        Fetch credentials for all users matching a Redis key pattern.
        :param pattern: glob-style pattern for user IDs
        :return: mapping user_id → creds dict
        """
        result = {}
        async for key in rds.scan_iter(match=pattern):
            creds = await self.get_credentials(key)
            if creds is not None:
                result[key] = creds
        return result