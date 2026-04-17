from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .common import track_activity, get_lang, send_error
from app.db import get_lang

async def age_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        track_activity(update)
        q = update.callback_query
        mode = q.data.replace("age_mode_", "")
        context.user_data["mode"] = f"age_calc_{mode}"
        msg = "Enter birthdate (DD/MM/YYYY):" if get_lang(update.effective_user.id) == "en" else "የትውልድ ቀንዎን ያስገቡ (ቀን/ወር/ዓመት)፦"
        await q.message.reply_text(msg)
        await q.answer()
    except Exception as e: await send_error(update, context, e, "age_callback")

async def contact_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_activity(update)
    q = update.callback_query
    context.user_data["mode"] = "contact_admin"
    msg = "✍️ Please type your message for the admin:" if get_lang(update.effective_user.id) == "en" else "✍️ እባክዎን ለአድሚኑ መልዕክትዎን ይጻፉ፦"
    await q.message.reply_text(msg, parse_mode="HTML")
    await q.answer()
