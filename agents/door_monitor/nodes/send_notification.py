from telegram import Bot
import asyncio
from dotenv import load_dotenv
import os

from agents.door_monitor.state import VLMState

# Load .env file
load_dotenv() 

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")



def send_telegram_notification(state: VLMState):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    async def send_message(text, chat_id):
        async with bot:
            await bot.send_message(text=text, chat_id=chat_id)

    async def run_bot(messages, chat_id):
        text = '\n'.join(messages)
        await send_message(text, chat_id)

    if state["family"] is True:
        messages = [
            f"Hello! A family member has arrived at the door. "
        ]  
    elif state["classification"] == 'mailman':
        messages = [
            f"Hi there! The mailman has just delivered a package for you."
        ] 
    elif state['classification'] == 'suspicious':
        messages = [
            f"Alert! Suspicious activity detected at the door. You might want to review the videos and call the authorities. "
        ]


    if messages:
        asyncio.run(run_bot(messages, CHAT_ID))
    
    return state