import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
import os

from preferences import get_prefs, set_pref

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
RECORDINGS_DIR = "../recordings"  

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------
# COMMANDS
# -----------------------------------------------------------

async def preferences_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prefs = get_prefs()

    msg = (
        "🔧 *Notification Preferences:*\n\n"
        f"👨‍👩‍👦 Family notifications: {'ON' if prefs['family'] else 'OFF'}\n"
        f"📬 Mail notifications: {'ON' if prefs['mail'] else 'OFF'}\n"
        f"⚠️ Suspicious activity: {'ON' if prefs['suspicious'] else 'OFF'}\n"
        f"🌙 Nighttime alerts: {'ON' if prefs['nighttime'] else 'OFF'}\n\n"
        "Use:\n"
        "`/setpref <family|mail|suspicious|nighttime> <on/off>`\n\n"
        "Example:\n"
        "`/setpref mail off`"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


async def setpref_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /setpref <family|mail|suspicious|nighttime> <on/off>")
        return

    pref, value = context.args
    pref = pref.lower()
    value = value.lower()

    if pref not in ["family", "mail", "suspicious", "nighttime"]:
        await update.message.reply_text("Invalid option.")
        return

    if value not in ["on", "off"]:
        await update.message.reply_text("Value must be 'on' or 'off'.")
        return

    set_pref(pref, value == "on")
    await update.message.reply_text(f"Updated: {pref} → {value.upper()}")


# Example notification handler (you can call this anywhere in your system)
async def send_family_alert(update: Update):
    prefs = get_prefs()
    if prefs["family"]:
        await update.message.reply_text("👨‍👩‍👦 Family member detected at the door!")


async def send_mail_alert(update: Update):
    prefs = get_prefs()
    if prefs["mail"]:
        await update.message.reply_text("📬 Mail has arrived!")


async def send_suspicious_alert(update: Update):
    prefs = get_prefs()
    if prefs["suspicious"]:
        await update.message.reply_text("⚠️ Suspicious activity detected!")


async def send_nighttime_alert(update: Update):
    prefs = get_prefs()
    if prefs["nighttime"]:
        await update.message.reply_text("🌙 Motion detected during nighttime!")


# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("preferences", preferences_command))
    application.add_handler(CommandHandler("setpref", setpref_command))

    application.run_polling()

if __name__ == "__main__":
    main()
