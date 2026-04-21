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
                "<b>🚀 የፈጣን ጅምር መመሪያ (v1)</b>\n\n"
                "<b>1️⃣ ቀን ለመቀየር:</b>\n"
                f"<code>https://ethio-calendar-bot.onrender.com/api/convert?date=DD/MM/YYYY&to=eth&key={api_key}</code>\n\n"
                "<b>2️⃣ የዛሬን ቀን ለማግኘት:</b>\n"
                f"<code>https://ethio-calendar-bot.onrender.com/api/today?key={api_key}</code>\n\n"
                "<b>3️⃣ ዕድሜ ለመቁጠር:</b>\n"
                f"<code>https://ethio-calendar-bot.onrender.com/api/age?date=DD/MM/YYYY&from=gc&key={api_key}</code>\n\n"
                "💡 <b>ፕሮፌሽናል አጠቃቀም:</b> ለበለጠ ደህንነት ቁልፉን በ Header (<code>Authorization: Bearer</code>) መጠቀም ይመከራል።\n\n"
                "🔗 <b>ሙሉ ሰነድ (Full Docs):</b> <i>ለዝርዝር መረጃ የኤፒአይ መመሪያውን ይመልከቱ።</i>"
            )
        else:
            msg = (
                "🔐 <b>Your Secure Developer API Key</b>\n\n"
                f"<code>{api_key}</code>\n\n"
                "⚠️ <b>IMPORTANT:</b> Keep this key secret. If compromised, you can regenerate a new one anytime.\n\n"
                "<b>🚀 Quick Start Documentation (v1)</b>\n\n"
                "<b>1️⃣ Date Conversion:</b>\n"
                f"<code>https://ethio-calendar-bot.onrender.com/api/convert?date=DD/MM/YYYY&to=eth&key={api_key}</code>\n\n"
                "<b>2️⃣ Get Today's Date:</b>\n"
                f"<code>https://ethio-calendar-bot.onrender.com/api/today?key={api_key}</code>\n\n"
                "<b>3️⃣ Age Calculator:</b>\n"
                f"<code>https://ethio-calendar-bot.onrender.com/api/age?date=DD/MM/YYYY&from=gc&key={api_key}</code>\n\n"
                "💡 <b>Security Tip:</b> Use <code>Authorization: Bearer</code> header instead of URL parameters for production apps.\n\n"
                "🔗 <b>Developer Portal:</b> <i>For full JSON schemas and examples, refer to our official API Guide.</i>"
            )
        keyboard = [
            [InlineKeyboardButton("📄 Download API Guide (PDF)", callback_data="api_download_guide")]
        ]
            
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
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
            if get_lang(uid) == "am":
                msg = "✍️ <b>ኤ ፒ አይ ለመሰረዝ መለያ ቁጥር (ID) ያስገቡ፦</b>\n\nእባክዎን ኤፒአይ ቁልፉ እንዲሰረዝ የሚፈልጉትን የተጠቃሚ መለያ ቁጥር (User ID) ከታች ይጻፉ።"
            else:
                msg = "✍️ <b>API Revocation Mode Active.</b>\n\nPlease enter the <b>User ID</b> you want to revoke API access for:"
            await query.message.reply_text(msg, parse_mode="HTML")
            await query.answer()
        elif data == "api_download_guide":
            await api_download_guide_handler(update, context)
        elif data == "api_broadcast_prompt":
            context.user_data["mode"] = "admin_api_broadcast_input"
            if get_lang(uid) == "am":
                msg = "📢 <b>ለኤፒአይ ተጠቃሚዎች መልዕክት ማስተላለፊያ</b>\n\nለሁሉም የኤፒአይ ተጠቃሚዎች ማስተላለፍ የሚፈልጉትን መልዕክት ከታች ይጻፉ።"
            else:
                msg = "📢 <b>Broadcast to Developers</b>\n\nPlease type the broadcast message you want to send to all API users."
            await query.message.reply_text(msg, parse_mode="HTML")
            await query.answer()
            
    except Exception as e:
        await send_error(update, context, e, "api_stats_callback")

async def api_download_guide_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the API guide download request."""
    try:
        query = update.callback_query
        uid = update.effective_user.id
        import os
        pdf_path = "assets/api_guide.pdf"
        if os.path.exists(pdf_path):
            await query.message.reply_document(
                document=open(pdf_path, "rb"),
                filename="Pagume_API_Guide.pdf",
                caption="📄 <b>Pagume Bot API - Full Documentation (v1.0)</b>\n\nIncluded: JSON Schemas, Examples, and Support contact details.",
                parse_mode="HTML"
            )
        else:
            msg = "❌ Documentation file not found on server. Please contact support@pagumebot.com" if get_lang(uid) == "en" else "❌ የሰነድ ፋይሉ አልተገኘም። እባክዎን support@pagumebot.com ያግኙ።"
            await query.message.reply_text(msg)
        await query.answer()
    except Exception as e:
        await send_error(update, context, e, "api_download_guide_handler")

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
            msg += f"{i}. <b>{html.escape(name)}</b> (<code>{uid}</code>)\n"
            msg += f"   └>> 🔑 <code>{key}</code> | <b>{count}</b> requests\n"
            msg += f"   └>> 🕒 Created: {str(created)[:16]}\n\n"
            
        # Pagination & Utility Buttons
        buttons = []
        total_pages = (total_api_users + per_page - 1) // per_page
        
        # Navigation row
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"api_dash:{page-1}"))
        
        # Current page / Total pages indicator or Refresh
        nav_row.append(InlineKeyboardButton(f"🔄 Refresh ({page+1}/{total_pages})", callback_data=f"api_dash:{page}"))
        
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"api_dash:{page+1}"))
        
        buttons.append(nav_row)
            
        # Add action buttons
        revoke_text = "🚫 Revoke Key" if lang != "am" else "🚫 ቁልፉን ሰርዝ"
        broadcast_text = "📢 Broadcast to Devs" if lang != "am" else "📢 ለዲቨሎፐሮች መልዕክት"
        
        buttons.append([
            InlineKeyboardButton(revoke_text, callback_data="api_revoke_prompt"),
            InlineKeyboardButton(broadcast_text, callback_data="api_broadcast_prompt")
        ])
        
        reply_markup = InlineKeyboardMarkup(buttons)
        
        if update.message:
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)
        else:
            try:
                await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)
            except Exception as e:
                # Catch "Message is not modified" which happens when refreshing data that hasn't changed
                if "Message is not modified" in str(e):
                    await update.callback_query.answer("Already up to date.")
                else:
                    raise e
            
    except Exception as e:
        await send_error(update, context, e, "send_api_stats_page")

async def handle_api_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the typed message to all API users."""
    try:
        if "mode" in context.user_data:
            context.user_data.pop("mode")
            
        broadcast_msg = update.message.text
        from app.db.api import get_all_api_user_ids
        targets = get_all_api_user_ids()
        
        if not targets:
            await update.message.reply_text("❌ No API users found in database.")
            return

        status_msg = await update.message.reply_text(f"🚀 <b>Starting API Broadcast to {len(targets)} developers...</b>", parse_mode="HTML")
        
        success_count = 0
        fail_count = 0
        
        import asyncio
        for uid in targets:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=f"📢 <b>API Developer Update</b>\n\n{broadcast_msg}",
                    parse_mode="HTML"
                )
                success_count += 1
            except Exception:
                fail_count += 1
            
            # Update progress every 10 users to keep admin informed
            if (success_count + fail_count) % 10 == 0:
                try:
                    await status_msg.edit_text(
                        f"⏳ <b>Broadcast in progress...</b>\n"
                        f"✅ Success: {success_count}\n"
                        f"❌ Failed: {fail_count}\n"
                        f"📊 Total: {len(targets)}",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            
            # Avoid hitting Telegram flood limits
            await asyncio.sleep(0.05)

        summary = (
            f"✅ <b>API Broadcast Complete</b>\n\n"
            f"📤 <b>Success:</b> {success_count}\n"
            f"❌ <b>Failed:</b> {fail_count}\n"
            f"👤 <b>Total Targets:</b> {len(targets)}"
        )
        await status_msg.edit_text(summary, parse_mode="HTML")
        
    except Exception as e:
        await send_error(update, context, e, "handle_api_broadcast_message")
