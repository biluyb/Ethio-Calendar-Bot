from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .common import track_activity, get_lang, send_error
from app.db import get_lang

async def age_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles calendar selection for age calculator."""
    try:
        track_activity(update)
        q = update.callback_query
        mode = q.data.replace("age_mode_", "")
        context.user_data["mode"] = f"age_calc_{mode}"
        
        lang = get_lang(update.effective_user.id)
        if lang == "en":
            msg = "✍️ <b>Birthdate Calendar Selected.</b>\n\nPlease enter your birthdate (DD/MM/YYYY):\n\nExample: <code>21/12/1995</code>"
        else:
            msg = "✍️ <b>የልደት ቀን መቁጠሪያ ተመርጧል።</b>\n\nእባክዎን የልደት ቀንዎን ያስገቡ (ቀን/ወር/ዓመት)፦\n\nለምሳሌ፦ <code>21/12/1988</code>"
            
        await q.message.reply_text(msg, parse_mode="HTML")
        await q.answer()
    except Exception as e: 
        await send_error(update, context, e, "age_callback")

async def contact_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles contact admin button click."""
    track_activity(update)
    q = update.callback_query
    context.user_data["mode"] = "contact_admin"
    
    lang = get_lang(update.effective_user.id)
    if lang == "en":
        msg = "✍️ <b>Standard Message Mode Active.</b>\n\nPlease type your message for the admin below:"
    else:
        msg = "✍️ <b>የመልዕክት መጻፊያ ገጽ።</b>\n\nእባክዎን ለአድሚኑ የሚልኩትን መልዕክት ከታች ይጻፉ፦"
        
    await q.message.reply_text(msg, parse_mode="HTML")
    await q.answer()
