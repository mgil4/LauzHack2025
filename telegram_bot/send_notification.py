from telegram import Bot
import asyncio
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv() 

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

#Define bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def send_message(text, chat_id):
    async with bot:
        await bot.send_message(text=text, chat_id=chat_id)

async def run_bot(messages, chat_id):
    text = '\n'.join(messages)
    await send_message(text, chat_id)

#Test messages
messages = [
    "Hi there! The mailman has just delivered a package for you."
]

if messages:
    asyncio.run(run_bot(messages, CHAT_ID))
