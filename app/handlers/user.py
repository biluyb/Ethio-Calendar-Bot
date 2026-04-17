import html
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommandScopeChat
from telegram.ext import ContextTypes
from .common import (
    get_menu, track_activity, track_group, check_blocked, send_error,
    EN_DAYS, EN_MONTHS, AM_DAYS, AM_MONTHS, INVITE_IMAGE_PATH, REDIRECT_IMAGE_URL,
    SUPER_ADMIN_CMDS, ADMIN_CMDS
)
from app.db import (
    get_lang, set_lang, get_user_details, get_top_referrers, get_referrers_count,
    is_admin_db, register_user
)
from app.utils import greg_to_eth
from app.texts import INFO_EN, INFO_AM
from app.config import ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update): return
    try:
        # Redirect group chat messages to DM before any other processing
        if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
            uid = update.effective_user.id if update.effective_user else None
            lang = get_lang(uid) if uid else "en"
            track_group(update)
            if uid: track_activity(update, "/start (Group)")
            
            bot_username = context.bot.username
            dm_url = f"https://t.me/{bot_username}?start=from_group"
            btn_text = "▶️ ቦቱን ክፈት" if lang == "am" else "▶️ Open Bot"
            keyboard = [[InlineKeyboardButton(btn_text, url=dm_url)]]
            if lang == "am":
                msg = (
                    "<b>ጳጉሜ ቦት</b>\n"
                    "<i> የኢትዮጵያ ቀን መቁጠሪያ እና የቀን መቀየሪያ።</i>\n\n"
                    "• <b>ትክክለኛ መቀየሪያ:</b> ከፈረንጅ ↔ ኢትዮጵያ\n"
                    "• <b>የዕድሜ ስሌት:</b> ፈጣን እና ትክክለኛ\n"
                    "• <b>በሁለት ቋንቋ:</b> አማርኛ እና እንግሊዝኛ\n"
                    "📩 <b>በተሟላ ሁኔታ ለመጠቀም ወደ ቦቱ ይሂዱ።</b>"
                )
            else:
                msg = (
                    "<b>Pagume Bot</b>\n"
                    "<i>The most advanced Ethiopian Calendar & Date Converter.</i>\n\n"
                    "• <b>Precise Conversion:</b> Gregorian ↔ Ethiopian\n"
                    "• <b>Age Calculator:</b> Fast and accurate\n"
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

        user = update.effective_user
        uid = user.id

        await update.message.chat.send_action(action="typing")

        username = user.username or user.full_name or str(uid)
        
        referred_by = None
        if context.args and context.args[0].isdigit():
            referrer_id = int(context.args[0])
            if referrer_id != uid: # Cannot refer self
                referred_by = referrer_id
        
        # Track activity and capture if user is new for referral logic
        is_new = register_user(uid, username, full_name=user.full_name, last_command="/start", referred_by=referred_by)
        track_group(update)

        # Notify referrer if this is a new registration
        if is_new and referred_by:
            try:
                ref_lang = get_lang(referred_by)
                user_data = get_user_details(referred_by)
                ref_count = user_data[10] if user_data else 1

                if ref_lang == "am":
                    notif = (
                        f"🎉 <b>እንኳን ደስ አለዎት!</b>\n\n"
                        f"<b>{username}</b> በእርስዎ ግብዣ መሠረት ቦቱን ተቀላቅሏል።\n\n"
                        f"📊 <b>ያጋበዙት ሰዎች ብዛት:</b> {ref_count}"
                    )
                else:
                    notif = (
                        f"🎉 <b>New Referral!</b>\n\n"
                        f"<b>{username}</b> has joined the bot using your invite link.\n\n"
                        f"📊 <b>Total invited:</b> {ref_count} people"
                    )
                await context.bot.send_message(chat_id=referred_by, text=notif, parse_mode="HTML")
            except Exception:
                pass # Referrer might have blocked the bot or ID is invalid

        lang = get_lang(uid)

        if lang == "am":
            text = "📅 እንኳን ደህና መጡ\n\nአማራጭ ይምረጡ:"
        else:
            text = "📅 Welcome to Ethio Date Converter\n\nSelect option:"

        await update.message.reply_text(text, reply_markup=get_menu(uid, lang))
        
        # Refresh commands on start if role changed or just to ensure correctness
        await refresh_user_commands(context.bot, uid)
    except Exception as e:
        await send_error(update, context, e, "start")   

async def refresh_user_commands(bot, uid):
    try:
        scope = BotCommandScopeChat(chat_id=uid)
        if uid in ADMIN_IDS:
            # Super Admin sees everything
            await bot.set_my_commands(SUPER_ADMIN_CMDS, scope=scope)
        elif is_admin_db(uid):
            # Regular Admin sees admin tools but not super admin tools
            await bot.set_my_commands(ADMIN_CMDS, scope=scope)
        else:
            # Regular user falls back to default commands
            await bot.delete_my_commands(scope=scope)
    except Exception as e:
        print(f"Failed to refresh commands for {uid}: {e}")

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id
        await update.message.chat.send_action(action="typing")
        
        lang = get_lang(uid)
        username = update.effective_user.username or update.effective_user.full_name or str(uid)
        track_activity(update, "Command: /today")

        now = datetime.now()

        # Gregorian
        g_day = now.day
        g_month = now.month
        g_year = now.year

        g_day_name = EN_DAYS[now.weekday()]
        g_month_name = EN_MONTHS[g_month - 1]

        # Ethiopian
        e_day, e_month, e_year = greg_to_eth(g_day, g_month, g_year)
        e_day_name = AM_DAYS[now.weekday()]
        e_month_name = AM_MONTHS[e_month - 1]

        if lang == "en":
            msg = f"Today \n\n🇺🇸 {g_day:02} - {g_month:02} - {g_year} | {g_day_name}, {g_month_name} - {g_day:02}\n"
            msg += f"🇪🇹 {e_day} - {e_month} - {e_year} | {e_day_name} - {e_month_name} - {e_day}"
        elif lang == "am":
            msg = f"ዛሬ \n\n🇺🇸 {g_day:02} - {g_month:02} - {g_year} | {g_day_name}, {g_month_name} - {g_day:02}\n"
            msg += f"🇪🇹 {e_day} - {e_month} - {e_year} | {e_day_name} - {e_month_name} - {e_day}"

        await update.message.reply_text(msg, reply_markup=get_menu(uid, lang))
    except Exception as e:
        await send_error(update, context, e, "today")

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id

        new_lang = "am" if get_lang(uid) == "am" else "en"
        set_lang(uid, new_lang)

        if new_lang == "am":
            msg = "✅ ቋንቋ ወደ አማርኛ ተቀይሯል"
        else:
            msg = "✅ Language changed to English"

        await update.message.reply_text(msg, reply_markup=get_menu(uid, new_lang))
        
    except Exception as e:
        await send_error(update, context, e, "lang")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)

        if lang == "am":
            await update.message.reply_text(INFO_AM, parse_mode="HTML")
        else:
            await update.message.reply_text(INFO_EN, parse_mode="HTML")

    except Exception as e:
        await send_error(update, context, e, "info")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides information about the bot and developer."""
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        
        if lang == "am":
            info_prefix = "የቦት መረጃ\n\nበ ShademT የተሰራ\n\n© May 2026\n\n"
            add_text = "➕ ወደ ግሩፕ አስገባ"
            contact_text = "📩 አድሚኑን ያግኙ"
        else:
            info_prefix = "<b>Bot Information:</b>\n\nDeveloped by ShademT\n\n© May 2026\n\n"
            add_text = "➕ Add to Group"
            contact_text = "📩 Contact Admin"

        add_url = f"https://t.me/{context.bot.username}?startgroup=true"
        keyboard = [
            [InlineKeyboardButton(contact_text, callback_data="contact_admin_request")],
            [InlineKeyboardButton(add_text, url=add_url)]
        ]
        
        await update.message.reply_text(info_prefix, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await send_error(update, context, e, "about_command")

async def share_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates and sends a unique referral link for the user."""
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        bot_me = await context.bot.get_me()
        bot_username = bot_me.username
        share_link = f"https://t.me/{bot_username}?start={uid}"
        
        if lang == "am":
            text = (
                "<b>ጳጉሜ ቦት</b>\n"
                "<i>የኢትዮጵያ ቀን መቁጠሪያ እና ቀን መቀየሪያ ።</i>\n\n"
                "• <b>ትክክለኛ የቀን መቀየሪያ:</b> ከፈረንጅ ወደ ኢትዮጵያ\n"
                "• <b>የዕድሜ ስሌት:</b> ፈጣን እና ትክክለኛ\n"
                "• <b>በሁለት ቋንቋ:</b> አማርኛ እና እንግሊዝኛ\n"
                f"<b>መጋበዣ ሊንክ፦</b> {share_link}"
            )
        else:
            text = (
                "<b>Pagume Bot</b>\n"
                "<i>The most advanced Ethiopian Calendar & Date Converter.</i>\n\n"
                "• <b>Precise Conversion:</b> Gregorian ↔ Ethiopian\n"
                "• <b>Age Calculator:</b> Fast & accurate\n"
                "• <b>Bilingual Support:</b> English & Amharic\n"
                "• <b>Referral Rewards:</b> Advanced ranking system\n"
                "• <b>Admin Tools:</b> Real-time management\n\n"
                f"<b>Referral Link:</b> {share_link}"
            )

        try:
            with open(INVITE_IMAGE_PATH, "rb") as photo:
                await update.message.reply_photo(
                    photo=photo, 
                    caption=text, 
                    parse_mode="HTML",
                    reply_markup=get_menu(uid, lang)
                )
        except Exception:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=get_menu(uid, lang))

    except Exception as e:
        await send_error(update, context, e, "share_command")

async def ranks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to view the top referrers leaderboard."""
    try:
        await send_ranks_page(update, context, page=0)
    except Exception as e:
        await send_error(update, context, e, "ranks_command")

async def ranks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles pagination for the leaderboard."""
    try:
        track_activity(update)
        query = update.callback_query
        data = query.data # format: r:{page}
        page = int(data.split(":")[1])
        await send_ranks_page(update, context, page=page)
        await query.answer()
    except Exception as e:
        await send_error(update, context, e, "ranks_callback")

async def send_ranks_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Displays the paginated referral leaderboard."""
    try:
        per_page = 10
        offset = page * per_page
        
        top_users = get_top_referrers(limit=per_page, offset=offset)
        total_count = get_referrers_count()
    
        uid = update.effective_user.id
        lang = get_lang(uid)
        
        if lang == "am":
            title = "🏆 <b>ጥሩ ጋባዦች (Top Referrers)</b>\n\n"
            empty = "ገና ምንም መጋበዣዎች የሉም።"
        else:
            title = "🏆 <b>Top Referrers Leaderboard</b>\n\n"
            empty = "No referrals yet. Be the first to invite!"

        if not top_users and page == 0:
            if update.message:
                await update.message.reply_text(title + empty, parse_mode="HTML")
            else:
                await update.callback_query.edit_message_text(title + empty, parse_mode="HTML")
            return

        msg = title
        for i, (uid_r, uname, count) in enumerate(top_users, 1 + offset):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🎖"
            msg += f"{i}. {medal} <b>{uname}</b> — {count} invites\n"
        
        # Pagination buttons
        buttons = []
        total_pages = (total_count + per_page - 1) // per_page
        
        if page > 0:
            buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"r:{page-1}"))
        if page < total_pages - 1:
            buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"r:{page+1}"))
            
        reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None
        
        if update.message:
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)
        else:
            try:
                await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)
            except Exception as e:
                # Silently fail on "message not modified"
                if "Message is not modified" not in str(e):
                    raise e
    except Exception as e:
        await send_error(update, context, e, "send_ranks_page")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides a tailored help guide based on the user's role (User/Admin/Super-Admin)."""
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        is_admin = is_admin_db(uid) or uid in ADMIN_IDS
        is_super = uid in ADMIN_IDS

        if lang == "am":
            text = "<b>🆘 የቦቱ እርዳታ</b>\n\n"
            text += "<b>👤 የተጠቃሚ ትዕዛዞች:</b>\n"
            text += "/start - ቦቱን ለመጀመር\n"
            text += "/lang - ቋንቋ ለመቀየር\n"
            text += "/today - የዛሬን ቀን ለማየት\n"
            text += "/info - ስለ ቀን መቁጠሪያው ግንዛቤ\n"
            text += "/share - ጓደኞችን ይጋብዙ\n"
            text += "/about - ስለ ቦቱ መረጃ (አድሚኑን ለማግኘት)\n"
            text += "/api - የኤፒአይ ቁልፍ (API Key) ለመፍጠር\n"
            text += "/help - ይህንን የእርዳታ መልዕክት ለማሳየት\n"
            
            if is_admin:
                text += "\n<b>👑 የአስተዳዳሪ ትዕዛዞች:</b>\n"
                text += "/users - ስለ ተጠቃሚዎች መረጃ\n"
                text += "/groups - ቦቱ ያለባቸው ግሩፖች ዝርዝር\n"
                text += "/send_msg - ለተጠቃሚ መልዕክት ለመላክ\n"
                text += "/broadcast - ለሁሉም ተጠቃሚዎች መልዕክት ለመላክ\n"
                text += "/block - ተጠቃሚን ወይም ግሩፕን ለማገድ\n"
                text += "/unblock - የታገደን ተጠቃሚ ለማንሳት\n"
                text += "/leavegroup - ቦቱን ከግሩፕ ለማስወጣት (ID ያስፈልጋል)\n"
                text += "/api_stats - የኤፒአይ ስታቲስቲክስ እና ማኔጅመንት\n"
                
                if is_super:
                    text += "\n<b>🛡️ የሱፐር-አድሚን ትዕዛዞች:</b>\n"
                    text += "/addadmin - አዲስ አስተዳዳሪ ለመጨመር\n"
                    text += "/deladmin - አስተዳዳሪ ለመቀነስ\n"
                    text += "/listadmins - የአስተዳዳሪዎች ዝርዝር\n"

        else:
            text = "<b>🆘 Bot Help</b>\n\n"
            text += "<b>👤 User Commands:</b>\n"
            text += "/start - Start the bot\n"
            text += "/lang - Change language\n"
            text += "/today - Show today's date\n"
            text += "/info - Calendar information\n"
            text += "/share - Invite friends\n"
            text += "/about - Bot info (Contact Admin)\n"
            text += "/api - Generate Developer API Key\n"
            text += "/help - Show this help message\n"
            
            if is_admin:
                text += "\n<b>👑 Admin Commands:</b>\n"
                text += "/users - User dashboard\n"
                text += "/groups - List groups the bot is in\n"
                text += "/send_msg - Send DM to user\n"
                text += "/broadcast - Send message to all users\n"
                text += "/block - Block a user or group\n"
                text += "/unblock - Unblock a user or group\n"
                text += "/leavegroup - Force bot to leave a group (requires group ID)\n"
                text += "/api_stats - API statistics and management\n"
                
                if is_super:
                    text += "\n<b>🛡️ Super-Admin Commands:</b>\n"
                    text += "/addadmin - Add new admin\n"
                    text += "/deladmin - Remove admin\n"
                    text += "/listadmins - List all admins\n"

        await update.message.reply_text(text, parse_mode="HTML")

    except Exception as e:
        await send_error(update, context, e, "help_command")
