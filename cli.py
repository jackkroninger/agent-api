import asyncio
from langgraph.checkpoint.redis import AsyncRedisSaver
from agent import graph as g
import yaml

with open("config.yml", "r") as f: config = yaml.safe_load(f)

async def main():
    checkpointer = AsyncRedisSaver(config["redis"]["url"])
    await checkpointer.asetup()
    graph = g.workflow.compile(checkpointer=checkpointer) # compile graph w/ redis memory

    thread_id = str(input("Thread ID: "))

    while True:
        prompt = input(">>> ")
        if not prompt: break
        print("", end="")
        async for piece in g.chat(prompt, thread_id, graph):
            print(piece, end="")
        print()


if __name__ == "__main__":
    asyncio.run(main())