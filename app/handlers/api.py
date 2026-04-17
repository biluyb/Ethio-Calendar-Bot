import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .common import send_error, get_lang, is_admin_db
from app.db import (
    get_or_create_api_key, get_api_usage_stats, get_total_api_users,
    revoke_api_key_db
)

async def api_key_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows a user to generate or view their API key."""
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        api_key = get_or_create_api_key(uid)
        
        if not api_key:
            err = "❌ Failed to generate API Key." if lang == "en" else "❌ የኤፒአይ (API) ቁልፍ መፍጠር አልተቻለም።"
            await update.message.reply_text(err)
            return
            
        if lang == "am":
            msg = (
                "🔐 <b>የእርስዎ የግል ኤፒአይ ቁልፍ (Secure API Key)</b>\n\n"
                f"<code>{api_key}</code>\n\n"
                "⚠️ <b>ማስጠንቀቂያ:</b> ይህንን ቁልፍ ለማንም አሳልፈው አይስጡ! ቁልፉ ከጠፋብዎት ሌላ አዲስ ማመንጨት ይችላሉ።\n\n"
                "<b>🚀 የኤፒአይ አጠቃቀም መመሪያ (API Guide)</b>\n\n"
                "<b>1️⃣ ቀን ለመቀየር (Convert):</b>\n"
                "<i>ከጎርጎርዮሳዊ ወደ ኢትዮጵያ ወይም በተቃራኒው ለመቀየር</i>\n"
                f"<code>/api/convert?date=DD/MM/YYYY&to_calendar=ethiopian&key={api_key}</code>\n\n"
                "<b>2️⃣ የዛሬን ቀን ለማግኘት (Today):</b>\n"
                "<i>ሁለቱንም የዛሬ ቀናቶች በአንድ ጊዜ ለማግኘት</i>\n"
                f"<code>/api/today?key={api_key}</code>\n\n"
                "<b>3️⃣ ዕድሜ ለመቁጠር (Age Calculator):</b>\n"
                "<i>በትክክለኛ የኢትዮጵያ ወራት ዕድሜን ለማስላት</i>\n"
                f"<code>/api/age?birth_date=DD/MM/YYYY&calendar=gregorian&key={api_key}</code>\n\n"
                "💡 <b>ማሳሰቢያ:</b> ለበለጠ መረጃ እና ለሙሉ ዳታ መልሶችን ለማየት የኤፒአይ ሰነዱን ይመልከቱ።"
            )
        else:
            msg = (
                "🔐 <b>Your Secure Developer API Key</b>\n\n"
                f"<code>{api_key}</code>\n\n"
                "⚠️ <b>IMPORTANT:</b> Keep this key secret. If compromised, you can regenerate a new one anytime.\n\n"
                "<b>🚀 Quick Start Documentation</b>\n\n"
                "<b>1️⃣ Date Conversion:</b>\n"
                "<i>Convert between Gregorian and Ethiopian calendars.</i>\n"
                f"<code>/api/convert?date=DD/MM/YYYY&to_calendar=ethiopian&key={api_key}</code>\n\n"
                "<b>2️⃣ Get Today's Date:</b>\n"
                "<i>Fetch both current dates in a single request.</i>\n"
                f"<code>/api/today?key={api_key}</code>\n\n"
                "<b>3️⃣ Age Calculator:</b>\n"
                "<i>Calculates precise age including Ethiopian months.</i>\n"
                f"<code>/api/age?birth_date=DD/MM/YYYY&calendar=gregorian&key={api_key}</code>\n\n"
                "💡 <b>Tip:</b> You can use <code>Authorization: Bearer YOUR_KEY</code> header instead of the URL parameter for better security."
            )
            
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        await send_error(update, context, e, "api_key_command")

async def api_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to launch the API dashboard."""
    try:
        uid = update.effective_user.id
        if not is_admin_db(uid):
            return
        await send_api_stats_page(update, context, page=0)
    except Exception as e:
        await send_error(update, context, e, "api_stats_command")

async def api_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles interaction with the API dashboard."""
    try:
        query = update.callback_query
        uid = update.effective_user.id
        if not is_admin_db(uid):
            await query.answer("Unauthorized", show_alert=True)
            return
            
        data = query.data
        if data.startswith("api_dash:"):
            page = int(data.split(":")[1])
            await send_api_stats_page(update, context, page=page)
            await query.answer()
        elif data == "api_revoke_prompt":
            context.user_data["mode"] = "admin_api_revoke_input"
            await query.message.reply_text("🔢 Please enter the <b>User ID</b> you want to revoke API access for:", parse_mode="HTML")
            await query.answer()
            
    except Exception as e:
        await send_error(update, context, e, "api_stats_callback")

async def send_api_stats_page(update, context, page: int = 0):
    """Displays a list of all users with API keys and their usage counts."""
    try:
        per_page = 10
        offset = page * per_page
        
        stats = get_api_usage_stats(limit=per_page, offset=offset)
        total_api_users = get_total_api_users()
        
        uid_admin = update.effective_user.id
        lang = get_lang(uid_admin)

        if lang == "am":
             title = "📊 <b>የኤፒአይ ማኔጅመንት ዳሽቦርድ</b>\n"
             total_str = f"<i>ጠቅላላ የኤፒአይ ተጠቃሚዎች: {total_api_users}</i>\n\n"
             no_keys = "እስካሁን ምንም የኤፒአይ ቁልፎች አልተፈጠሩም።"
        else:
             title = "📊 <b>API Management Dashboard</b>\n"
             total_str = f"<i>Total API Users: {total_api_users}</i>\n\n"
             no_keys = "No API keys generated yet."

        msg = title + total_str
        
        if not stats:
            msg += no_keys
            if update.message:
                await update.message.reply_text(msg, parse_mode="HTML")
            else:
                await update.callback_query.edit_message_text(msg, parse_mode="HTML")
            return

        for i, (uid, uname, fname, key, count, created) in enumerate(stats, 1 + offset):
            name = fname or uname or f"ID:{uid}"
            short_key = f"{key[:6]}...{key[-4:]}"
            msg += f"{i}. <b>{html.escape(name)}</b> (<code>{uid}</code>)\n"
            msg += f"   └>> 🔑 <code>{short_key}</code> | 🚀 <b>{count}</b> requests\n"
            msg += f"   └>> 🕒 Created: {str(created)[:16]}\n\n"
            
        # Pagination & Utility Buttons
        buttons = []
        total_pages = (total_api_users + per_page - 1) // per_page
        
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"api_dash:{page-1}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"api_dash:{page+1}"))
        if nav_row:
            buttons.append(nav_row)
            
        # Add Revoke action button (prompt for ID)
        revoke_text = "🚫 Revoke Key" if lang != "am" else "🚫 ቁልፉን ሰርዝ"
        buttons.append([InlineKeyboardButton(revoke_text, callback_data="api_revoke_prompt")])
        
        reply_markup = InlineKeyboardMarkup(buttons)
        
        if update.message:
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)
            
    except Exception as e:
        await send_error(update, context, e, "send_api_stats_page")
