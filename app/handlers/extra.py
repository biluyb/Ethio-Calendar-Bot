import os
from telegram import Update
from telegram.ext import ContextTypes
from .common import get_lang, is_admin_db, send_error
from app.config import ADMIN_IDS, BOT_TOKEN

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        is_admin = is_admin_db(uid) or uid in ADMIN_IDS
        text = "<b>🆘 Help</b>\n\n- /start: Start\n- /today: Today's date\n- /api: API key" if lang=="en" else "<b>🆘 እርዳታ</b>\n\n- /start: ለመጀመር\n- /today: የዛሬ ቀን\n- /api: የኤፒአይ ቁልፍ"
        if is_admin: text += "\n\n<b>👑 Admin:</b> /users, /groups, /broadcast"
        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e: await send_error(update, context, e, "help")

async def health_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    url = os.getenv("WEBHOOK_URL")
    if not url: return await update.message.reply_text("❌ No Webhook URL")
    await update.message.reply_text(f"🟢 Cron link: <code>{url}/{BOT_TOKEN}</code>", parse_mode="HTML")
