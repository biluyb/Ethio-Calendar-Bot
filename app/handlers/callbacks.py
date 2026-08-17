from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .common import track_activity, get_lang, send_error, check_blocked

async def age_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles calendar selection for age calculator."""
    if await check_blocked(update): return
    try:
        track_activity(update)
        q = update.callback_query
        mode = q.data.replace("age_mode_", "")
        
        lang = get_lang(update.effective_user.id)
        if mode == "start":
            if lang == "am":
                prompt = "<b>🎂 የዕድሜ ስሌት</b>\n\nእባክዎን የልደት ቀንዎ የተመዘገበበትን የቀን አቆጣጠር ይምረጡ፦"
                keyboard = [[
                    InlineKeyboardButton("🇺🇸 Gregorian", callback_data="age_mode_gc"),
                    InlineKeyboardButton("🇪🇹 Ethiopian", callback_data="age_mode_et")
                ]]
            else:
                prompt = "<b>🎂 Age Calculator</b>\n\nSelect the calendar system used for your birthdate:"
                keyboard = [[
                    InlineKeyboardButton("🇺🇸 Gregorian", callback_data="age_mode_gc"),
                    InlineKeyboardButton("🇪🇹 Ethiopian", callback_data="age_mode_et")
                ]]
            await q.message.reply_text(prompt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            await q.answer()
            return

        context.user_data["mode"] = f"age_calc_{mode}"
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
    if await check_blocked(update): return
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
