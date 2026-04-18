import os
from telegram import Update
from telegram.ext import ContextTypes
from .common import get_lang, is_admin_db, send_error
from app.config import ADMIN_IDS, BOT_TOKEN

async def health_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    url = os.getenv("WEBHOOK_URL")
    if not url: return await update.message.reply_text("❌ No Webhook URL")
    await update.message.reply_text(f"🟢 Cron link: <code>{url}/{BOT_TOKEN}</code>", parse_mode="HTML")
