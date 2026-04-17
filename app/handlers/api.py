import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .common import send_error, get_lang, is_admin_db
from app.db import (
    get_or_create_api_key, get_api_usage_stats, get_total_api_users,
    revoke_api_key_db
)

async def api_key_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        key = get_or_create_api_key(uid)
        if not key: return await update.message.reply_text("❌ Failed to generate key.")
        
        if lang == "am":
            msg = (
                "🔐 <b>የእርስዎ የግል ኤፒአይ ቁልፍ (Secure API Key)</b>\n\n"
                f"<code>{key}</code>\n\n"
                "⚠️ <b>ማስጠንቀቂያ:</b> ይህንን ቁልፍ ለማንም አሳልፈው አይስጡ!\n\n"
                "<b> የኤፒአይ አጠቃቀም መመሪያ (API Guide)</b>\n\n"
                "<b>1️⃣ ቀን ለመቀየር (Convert):</b>\n"
                f"<code>/api/convert?date=DD/MM/YYYY&to_calendar=ethiopian&key={key}</code>\n\n"
                "<b>2️⃣ የዛሬን ቀን ለማግኘት (Today):</b>\n"
                f"<code>/api/today?key={key}</code>\n\n"
                "<b>3️⃣ ዕድሜ ለመቁጠር (Age Calculator):</b>\n"
                f"<code>/api/age?birth_date=DD/MM/YYYY&calendar=gregorian&key={key}</code>"
            )
        else:
            msg = (
                "🔐 <b>Your Secure Developer API Key</b>\n\n"
                f"<code>{key}</code>\n\n"
                "⚠️ <b>IMPORTANT:</b> Keep this key secret.\n\n"
                "<b> Quick Start Documentation</b>\n\n"
                "<b>1️⃣ Date Conversion:</b>\n"
                f"<code>/api/convert?date=DD/MM/YYYY&to_calendar=ethiopian&key={key}</code>\n\n"
                "<b>2️⃣ Get Today's Date:</b>\n"
                f"<code>/api/today?key={key}</code>\n\n"
                "<b>3️⃣ Age Calculator:</b>\n"
                f"<code>/api/age?birth_date=DD/MM/YYYY&calendar=gregorian&key={key}</code>"
            )
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e: await send_error(update, context, e, "api_key")

async def api_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_db(update.effective_user.id): return
    await send_api_stats_page(update, context, 0)

async def api_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin_db(update.effective_user.id): return
    data = query.data
    if data.startswith("api_dash:"):
        await send_api_stats_page(update, context, int(data.split(":")[1]))
    elif data == "api_revoke_prompt":
        context.user_data["mode"] = "admin_api_revoke_input"
        await query.message.reply_text("🔢 Enter User ID to revoke:")
    await query.answer()

async def send_api_stats_page(update, context, page):
    try:
        per = 10
        stats = get_api_usage_stats(limit=per, offset=page*per)
        total = get_total_api_users()
        msg = f"📊 <b>API Stats</b> (Total: {total})\n\n"
        for i, s in enumerate(stats, 1 + page*per):
            msg += f"{i}. <b>{s[1]}</b>: {s[4]} requests\n   🔑 <code>{s[3][:6]}...</code>\n"
        
        kb = []
        nav = []
        if page > 0: nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"api_dash:{page-1}"))
        if (page+1)*per < total: nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"api_dash:{page+1}"))
        if nav: kb.append(nav)
        kb.append([InlineKeyboardButton("🚫 Revoke Key", callback_data="api_revoke_prompt")])
        
        await (update.message.reply_text if update.message else update.callback_query.edit_message_text)(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e: await send_error(update, context, e, "api_stats_page")
