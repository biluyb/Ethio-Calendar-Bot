import html
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .common import (
    track_activity, get_lang, send_error, get_menu, check_blocked, track_group,
    EN_DAYS, EN_MONTHS, AM_DAYS, AM_MONTHS, INVITE_IMAGE_PATH, REDIRECT_IMAGE_URL
)
from .user import today, share_command
from .api import api_key_command, api_stats_command
from app.db import (
    set_lang, get_lang, is_admin_db, revoke_api_key_db, get_admins_db, 
    get_user_by_id, get_user_by_username
)
from app.utils import eth_to_greg, greg_to_eth, calculate_age
from app.config import ADMIN_IDS

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main message handler that routes text input to appropriate sub-handlers."""
    if await check_blocked(update): return
    
    track_activity(update)

    try:
        # Redirect group chat messages to DM before any other processing
        if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
            if update.message and update.message.text:
                uid = update.effective_user.id if update.effective_user else None
                lang = get_lang(uid) if uid else "en"
                track_group(update)
                bot_username = context.bot.username
                dm_url = f"https://t.me/{bot_username}?start=from_group"
                btn_text = "▶️ ቦቱን ክፈት" if lang == "am" else "▶️ Open Bot"
                keyboard = [[InlineKeyboardButton(btn_text, url=dm_url)]]
                if lang == "am":
                    msg = (
                        "<b>ጳጉሜ ቦት</b>\n"
                        "<i>የኢትዮጵያ ቀን መቁጠሪያ እና ቀን መቀየሪያ ።</i>\n\n"
                        "• <b>ትክክለኛ መቀየሪያ:</b> ከፈረንጅ ወደ  ኢትዮጵያ\n"
                        "• <b>የዕድሜ ስሌት:</b> ፈጣን እና ትክክለኛ\n"
                        "• <b>በሁለት ቋንቋ:</b> አማርኛ እና እንግሊዝኛ\n"
                        "📩 <b>ተሟላ ሁኔታ ለመጠቀም ወደ ቦቱ ይሂዱ።</b>"
                    )
                else:
                    msg = (
                        "<b>Pagume Bot</b>\n"
                        "<i>The most advanced Ethiopian Calendar & Date Converter.</i>\n\n"
                        "• <b>Precise Conversion:</b> Gregorian ↔ Ethiopian\n"
                        "• <b>Age Calculator:</b> Fast & accurate\n"
                        "• <b>Bilingual Support:</b> English & Amharic\n"
                        "• <b>Referral Rewards:</b> Advanced ranking system\n"
                        "• <b>Admin Tools:</b> Real-time management\n\n"
                        "📩 <b>Please use the bot in DM for the full experience.</b>"
                    )
                
                try:
                    with open(INVITE_IMAGE_PATH, "rb") as photo:
                        await update.message.reply_photo(
                            photo=photo, 
                            caption=msg, 
                            parse_mode="HTML",
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                except Exception:
                    await update.message.reply_photo(
                        photo=REDIRECT_IMAGE_URL, 
                        caption=msg, 
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            return

        if not update.message or not update.message.text:
            return

        uid = update.effective_user.id
        track_group(update)
        
        await update.message.chat.send_action(action="typing")
        
        text = update.message.text.strip()
        lang = get_lang(uid)

        # 1. Handle Menu Buttons & Navigation
        if await process_menu_commands(update, context, text, uid, lang):
            return

        # 2. Check if user is in a specific input mode
        if "mode" not in context.user_data:
            return

        mode = str(context.user_data["mode"])
        
        # Admin Contact & Reply Flows
        if mode == "contact_admin":
            return await handle_admin_contact_message(update, context)

        if mode.startswith("rep_"):
            return await handle_admin_reply_to_user(update, context)
            
        if mode == "admin_dm_send":
            from .admin import handle_admin_dm_send
            return await handle_admin_dm_send(update, context)
            
        if mode == "admin_api_revoke_input":
            try:
                target_uid = int(text)
                if revoke_api_key_db(target_uid):
                    await update.message.reply_text(f"✅ API Key for User ID <code>{target_uid}</code> has been revoked.", parse_mode="HTML")
                else:
                    await update.message.reply_text("❌ Could not revoke key. Verify the User ID exists.")
                context.user_data.pop("mode", None)
            except ValueError:
                await update.message.reply_text("❌ Please enter a valid numerical User ID.")
            return

        # 3. Process Date Input (for conversions and age)
        try:
            # Handle variations in date separators
            date_parts = text.replace("-", "/").split("/")
            if len(date_parts) != 3:
                raise ValueError("Invalid date format")
            d, m, y = map(int, date_parts)
        except (ValueError, TypeError):
            msg = (
                "❌ Invalid format. Please use DD/MM/YYYY\n\nExample: 21/12/2022" 
                if lang == "en" else 
                "❌ ትክክለኛ ያልሆነ የቀን አጻጻፍ. እባክዎ ቀን/ወር/ዓመት በ ቁጥር ያስገቡ\n\nለምሳሌ: 21/12/2012"
            )
            return await update.message.reply_text(msg)

        # 4. Perform Conversion based on Mode
        try:
            if mode == "g2e":
                await process_g2e(update, context, d, m, y, lang)
            elif mode == "e2g":
                await process_e2g(update, context, d, m, y, lang)
            elif mode.startswith("age_calc_"):
                await process_age_calc(update, context, d, m, y, lang, mode)
                
        except ValueError as e:
            error_str = str(e)
            
            # Smart Custom Error Messages
            if "Pagume in" in error_str:
                limit = 6 if "1-6" in error_str else 5
                user_msg = (
                    f"❌ Invalid date: Pagume only has {limit} days in {y}."
                    if lang == "en" else 
                    f"❌ ትክክለኛ ያልሆነ ቀን። ጳጉሜ በ {y} ዓ.ም {limit} ቀናት ብቻ ነው ያላት።"
                )
            elif "1-30 days" in error_str:
                user_msg = (
                    f"❌ Invalid date: Month {m} only has 30 days."
                    if lang == "en" else
                    f"❌ ትክክለኛ ያልሆነ ቀን። ወር {m} 30 ቀናት ብቻ ነው ያለው።"
                )
            elif "month must be in" in error_str.lower() or "Month must be between" in error_str:
                user_msg = (
                    "❌ Invalid date: Month must be between 1 and 12."
                    if lang == "en" else
                    "❌ ትክክለኛ ያልሆነ ቀን። ወር ከ 1 እስከ 12 መሆን አለበት።"
                )
            elif "day is out of range for month" in error_str:
                import calendar
                try:
                    max_days = calendar.monthrange(y, m)[1]
                    user_msg = (
                        f"❌ Invalid date: Month {m} only has {max_days} days in {y}."
                        if lang == "en" else
                        f"❌ ትክክለኛ ያልሆነ ቀን። በ {y} ዓ.ም ወር {m} {max_days} ቀናት ብቻ ነው ያለው።"
                    )
                except Exception:
                    user_msg = "❌ Invalid date range." if lang == "en" else "❌ ያስገቡት ቀን ለዛ ወር ትክክል አይደለም።"
            else:
                user_msg = (
                    "❌ Invalid date range. \nEnter date DD/MM/YYYY\n\nExample: 21/12/2022." 
                    if lang == "en" else 
                    "❌ ትክክለኛ ያልሆነ ቀን። እባክዎ በዚህ ቅርጽ ያስገቡ\nቀን/ወር/ዓመት\n\nለምሳሌ: 21/12/2012"
                )
            await update.message.reply_text(user_msg)
            
    except Exception as e:
        await send_error(update, context, e, "handle")

async def process_menu_commands(update, context, text, uid, lang):
    """Processes menu button clicks. Returns True if handled."""
    # Language Selection
    if text == "🇺🇸 English":
        set_lang(uid, "en")
        await update.message.reply_text("✅ Language set to English", reply_markup=get_menu(uid, "en"))
        return True
    if text == "🇪🇹 አማርኛ":
        set_lang(uid, "am")
        await update.message.reply_text("✅ ቋንቋ ወደ አማርኛ ተቀይሯል", reply_markup=get_menu(uid, "am"))
        return True

    # Main Features
    if text in ["📅 Today", "📅 ዛሬ"]:
        from .user import today
        await today(update, context)
        return True

    if text in ["🌐 Language", "🌐 ቋንቋ"]:
        keyboard = [["🇺🇸 English", "🇪🇹 አማርኛ"]]
        await update.message.reply_text("Choose language / ቋንቋ ይምረጡ", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return True

    if text in ["📩 Contact Admin", "📩 አድሚኑን ያግኙ", "📩   መልዕክት ላክ"]:
        context.user_data["mode"] = "contact_admin"
        if lang == "am":
            info_prefix = "የቦት መረጃ\n\nበ ShademT የተሰራ\n\n© May 2026\n\n"
            msg = info_prefix + "<b>✍️ እባክዎን መልዕክትዎን እዚህ ይጻፉ...</b>"
            add_text = "➕ ወደ ግሩፕ አስገባ"
        else:
            info_prefix = "<b>Bot Information:</b>\n\nDeveloped by ShademT\n\n© May 2026\n\n"
            msg = info_prefix + "<b>✍️ Please type your message below...</b>"
            add_text = "➕ Add to Group"

        add_url = f"https://t.me/{context.bot.username}?startgroup=true"
        keyboard = [
            [InlineKeyboardButton("📩 Contact Admin" if lang == "en" else "📩 አድሚኑን ያግኙ", callback_data="contact_admin_request")],
            [InlineKeyboardButton(add_text, url=add_url)]
        ]
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return True

    if text in ["🎂 Age Calculator", "🎂 የዕድሜ ስሌት"]:
        prompt = "Choose birthdate calendar:" if lang == "en" else "የልደት ቀን መቁጠሪያ ይምረጡ፦"
        keyboard = [[InlineKeyboardButton("Gregorian", callback_data="age_mode_gc"), 
                     InlineKeyboardButton("Ethiopian", callback_data="age_mode_et")]]
        await update.message.reply_text(prompt, reply_markup=InlineKeyboardMarkup(keyboard))
        return True

    if text in ["🤝 Invite Friends", "🤝 ጓደኞችን ይጋብዙ"]:
        from .user import share_command
        await share_command(update, context)
        return True

    if text in ["📅 Gregorian ➜ Ethiopian", "📅 ከፈረንጅ ወደ ኢትዮጵያ"]:
        context.user_data["mode"] = "g2e"
        prompt = "Enter date DD/MM/YYYY\n\nExample: 21/12/2022" if lang == "en" else "ቀን/ወር/ዓመት ያስገቡ\n\nለምሳሌ: 21/12/2012"
        await update.message.reply_text(prompt)
        return True

    if text in ["📆 Ethiopian ➜ Gregorian", "📆 ከኢትዮጵያ ወደ ፈረንጅ"]:
        context.user_data["mode"] = "e2g"
        prompt = "Enter date DD/MM/YYYY\n\nExample: 21/12/2022" if lang == "en" else "ቀን/ወር/ዓመት ያስገቡ\n\nለምሳሌ: 21/12/2012"
        await update.message.reply_text(prompt)
        return True

    if text in ["📢 Broadcast Message", "📢 መልዕክት ማስተላለፊያ (Broadcast)"]:
        if is_admin_db(uid) or uid in ADMIN_IDS:
            await update.message.reply_text("Usage: /broadcast <message>\n\nOr just type your message with the command.")
        return True

    if text in ["🔐 API (Developer)", "🔐 ኤፒአይ (Developer)"]:
        from .api import api_key_command
        await api_key_command(update, context)
        return True

    if text in ["📊 API Stats", "📊 ኤፒአይ ስታቲስቲክስ"]:
        from .api import api_stats_command
        await api_stats_command(update, context)
        return True

    return False

async def process_g2e(update, context, d, m, y, lang):
    """Internal logic to convert Gregorian date to Ethiopian and reply to user."""
    try:
        ed, em, ey = greg_to_eth(d, m, y)
        wk_day = datetime(y, m, d).weekday()
        msg = f"🇺🇸 {d:02} - {m:02} - {y} || {EN_DAYS[wk_day]}, {EN_MONTHS[int(m)-1]} - {d:02}\n"
        msg += f"🇪🇹 {ed} - {em} - {ey} || {AM_DAYS[wk_day]}, {AM_MONTHS[int(em)-1]} - {ed}"
        await update.message.reply_text(msg, reply_markup=get_menu(update.effective_user.id, lang))
        context.user_data.pop("mode", None)
    except ValueError as e:
        err_msg = str(e)
        user_msg = f"❌ Invalid date: {err_msg}\n\nExample: 21/12/2022" if lang == "en" else f"❌ የተሳሳተ ቀን: {err_msg}\n\nለምሳሌ: 21/12/2012"
        if "day is out of range for month" in err_msg:
             user_msg = "❌ The day you entered is not valid for that month." if lang == "en" else "❌ ያስገቡት ቀን ለዛ ወር ትክክል አይደለም።"
        elif "month must be in 1..12" in err_msg.lower():
             user_msg = "❌ Month must be between 1 and 12." if lang == "en" else "❌ ወር ከ 1 እስከ 12 መሆን አለበት።"
        await update.message.reply_text(user_msg)
    except Exception as e:
        await send_error(update, context, e, "process_g2e")

async def process_e2g(update, context, d, m, y, lang):
    """Internal logic to convert Ethiopian date to Gregorian and reply to user."""
    try:
        gd, gm, gy = eth_to_greg(d, m, y)
        wk_day = datetime(gy, gm, gd).weekday()
        msg = f"🇺🇸 {gd:02} - {gm:02} - {gy} || {EN_DAYS[wk_day]}, {EN_MONTHS[int(gm)-1]} \n"
        msg += f"🇪🇹 {d} - {m} - {y} || {AM_DAYS[wk_day]} - {AM_MONTHS[int(m)-1]} - {d} "
        await update.message.reply_text(msg, reply_markup=get_menu(update.effective_user.id, lang))
        context.user_data.pop("mode", None)
    except Exception as e:
        await send_error(update, context, e, "process_e2g")

async def process_age_calc(update: Update, context: ContextTypes.DEFAULT_TYPE, d: int, m: int, y: int, lang: str, mode: str):
    """Calculates age based on birthdate and provides bilingual output."""
    try:
        now = datetime.now()
        if mode == "age_calc_gc":
            birth_date = datetime(y, m, d)
            wk_day = birth_date.weekday()
            ed, em, ey = greg_to_eth(d, m, y)
            gd, gm, gy = d, m, y
        else:
            gd, gm, gy = eth_to_greg(d, m, y)
            birth_date = datetime(gy, gm, gd)
            wk_day = birth_date.weekday()
            ed, em, ey = d, m, y
        
        if birth_date > now:
            if lang == "am":
                err = "❌ የልደት ቀን ወደፊት መሆን አይችልም!"
            else:
                err = "❌ Birthdate cannot be in the future!"
            await update.message.reply_text(err, reply_markup=get_menu(update.effective_user.id, lang))
            context.user_data.pop("mode", None)
            return

        years, months, days = calculate_age(birth_date, now)
        
        # Professional result format
        msg = f"🇺🇸 {gd:02} - {gm:02} - {gy} | {EN_DAYS[wk_day]}, {EN_MONTHS[int(gm)-1]} - {gd:02}\n"
        msg += f"🇪🇹 {ed:02} - {em:02} - {ey} | {AM_DAYS[wk_day]} - {AM_MONTHS[int(em)-1]} - {ed:02}\n\n"
        msg += "━━━━━━━━━━━━━━━━━\n"
        
        if lang == "en":
            msg += f"🎂 <b>{years}</b> Years | <b>{months}</b> Months | <b>{days}</b> Days"
        else:
            msg += f"🎂 <b>{years}</b> ዓመት | <b>{months}</b> ወር | <b>{days}</b> ቀን"

        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=get_menu(update.effective_user.id, lang))
        context.user_data.pop("mode", None)
    except Exception as e:
        await send_error(update, context, e, "process_age_calc")

async def contact_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the inline 'Contact Admin' button click - prompts user to type their message."""
    track_activity(update)
    query = update.callback_query
    uid = update.effective_user.id
    lang = get_lang(uid)

    context.user_data["mode"] = "contact_admin"
    if lang == "am":
        msg = "✍️ <b>እባክዎን ለአድሚኑ መላክ የሚፈልጉትን መልዕክት ይጻፉ።</b>"
    else:
        msg = "✍️ <b>Please type the message you want to send to the admin.</b>"

    await query.message.reply_text(msg, parse_mode="HTML")
    await query.answer()

async def handle_admin_contact_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes the message intended for admins and forwards it."""
    uid = update.effective_user.id
    lang = get_lang(uid)
    user_text = update.message.text
    user = update.effective_user
    
    # Format message for admin
    esc_name = html.escape(user.full_name or "Unknown")
    esc_uname = html.escape(user.username or "N/A")
    esc_text = html.escape(user_text[:1000]) # Truncate to 1000 chars

    sender_info = f"👤 <b>From:</b> {esc_name} (@{esc_uname})\n🆔 <b>ID:</b> <code>{uid}</code>"
    admin_msg = f"✉️ <b>New Message to Admin</b>\n\n{sender_info}\n\n📝 <b>Message:</b>\n{esc_text}"
    
    try:
        if lang == "am":
            confirm = "✅ መልዕክትዎ ለአድሚኑ ተልኳል። እናመሰግናለን!"
        else:
            confirm = "✅ Your message has been sent to the admin. Thank you!"
            
        await update.message.reply_text(confirm, reply_markup=get_menu(uid, lang))
        
        if "mode" in context.user_data:
            del context.user_data["mode"]

        admins = set(get_admins_db()) | set(ADMIN_IDS)
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Reply", callback_data=f"admin_reply_{uid}")]])
        
        for admin_id in admins:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_msg,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            except Exception:
                pass
            
    except Exception as e:
        await send_error(update, context, e, "handle_admin_contact_message")

async def admin_reply_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Reply' button click by an admin."""
    track_activity(update)
    query = update.callback_query
    uid = update.effective_user.id
    
    if not is_admin_db(uid):
        await query.answer("Unauthorized", show_alert=True)
        return
        
    target_uid = query.data.replace("admin_reply_", "")
    context.user_data["mode"] = f"rep_{target_uid}"
    
    await query.message.reply_text(f"✍️ <b>Replying to User:</b> <code>{target_uid}</code>\n\nPlease type your message below:", parse_mode="HTML")
    await query.answer()

async def handle_admin_reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes the admin's reply and sends it back to the user."""
    admin_uid = update.effective_user.id
    mode = context.user_data.get("mode", "")
    target_uid = int(mode.replace("rep_", ""))
    reply_text = update.message.text
    
    admin_info = "📨 <b>Message from Admin</b>\n\n"
    final_msg = f"{admin_info}{reply_text}"
    
    try:
        await context.bot.send_message(
            chat_id=target_uid,
            text=final_msg,
            parse_mode="HTML"
        )
        
        await update.message.reply_text(f"✅ Reply sent to user <code>{target_uid}</code>", parse_mode="HTML")
        
        if "mode" in context.user_data:
            del context.user_data["mode"]
            
    except Exception as e:
        await send_error(update, context, e, "handle_admin_reply_to_user")

async def unknown_command(update, context):
    """Fallback handler for unrecognized commands."""
    await update.message.reply_text("❌ Unknown command. Use /help", reply_markup=get_menu(update.effective_user.id, get_lang(update.effective_user.id)))
