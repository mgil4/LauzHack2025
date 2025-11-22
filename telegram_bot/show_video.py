import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
RECORDINGS_DIR = "../recordings"  

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def show_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /show <id>")
        return

    video_id = args[0]
    video_filename = f"recording_{video_id}.MOV"
    video_path = os.path.join(RECORDINGS_DIR, video_filename)

    if os.path.exists(video_path):
        # Send video
        await update.message.reply_video(video=open(video_path, "rb"))
        logger.info("Sent video %s to user %s", video_filename, update.message.from_user.first_name)
    else:
        await update.message.reply_text(f"No video found for id {video_id}")
        logger.info("Video %s not found for user %s", video_filename, update.message.from_user.first_name)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("show", show_command))
    application.run_polling()

if __name__ == "__main__":
    main()
