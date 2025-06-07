from redis import Redis
from fastapi import FastAPI
import yaml

with open("config.yml") as f:
    config = yaml.safe_load(f)

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