import sys, asyncio
from telethon import TelegramClient
from dotenv import load_dotenv
import os

load_dotenv()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_NAME = os.environ.get("SESSION_NAME", "forwarder")

async def main():
    if len(sys.argv) < 2:
        print("Uso: python whois.py <@usuario | link | -100id>")
        return
    query = sys.argv[1]
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        ent = await client.get_entity(query)
        print("Título:", getattr(ent, "title", "N/A"))
        print("ID:", ent.id)
        if ent.id < 0:
            print("Chat ID para .env:", ent.id)
        else:
            print("Chat ID para .env:", f"-100{ent.id}")

if __name__ == "__main__":
    asyncio.run(main())
