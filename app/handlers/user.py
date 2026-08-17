import html
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommandScopeChat
from telegram.ext import ContextTypes
from .common import (
    get_menu, track_activity, track_group, check_blocked, send_error,
    EN_DAYS, EN_MONTHS, AM_DAYS, AM_MONTHS, INVITE_IMAGE_PATH, REDIRECT_IMAGE_URL,
    SUPER_ADMIN_CMDS, ADMIN_CMDS, get_share_keyboard
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

        # Today Details
        from app.holidays import get_day_type, TYPE_EMOJI
        from app.handlers.calendar_view import get_evangelist, get_current_eth_date

        g_day, g_month, g_year = now.day, now.month, now.year
        g_day_name = EN_DAYS[now.weekday()]
        g_month_name = EN_MONTHS[g_month - 1]

        e_day, e_month, e_year = greg_to_eth(g_day, g_month, g_year)
        e_day_name = AM_DAYS[now.weekday()]
        e_month_name = AM_MONTHS[e_month - 1]
        evangelist = get_evangelist(e_year)

        hol = get_day_type(e_month, e_day, e_year)

        tey, tem, _ = get_current_eth_date()

        # Build requested format:
        # 🇺🇸 08 - 07 - 2026 | Wednesday, July - 08
        # 🇪🇹 1 - 11 - 2018 | ረቡዕ - ሐምሌ - 1
        greg_formatted = f"🇺🇸 {g_day:02d} - {g_month:02d} - {g_year} | {g_day_name}, {g_month_name} - {g_day:02d}"
        
        if lang == "am":
            eth_formatted = f"🇪🇹 {e_day} - {e_month} - {e_year} | {e_day_name} - {e_month_name} - {e_day}"
            eva_txt = f" (ዘመነ {evangelist['am']})" if evangelist else ""
            msg = (
                f"📅 <b>የዛሬ ቀን መረጃ (Today)</b>\n\n"
                f"<code>{greg_formatted}</code>\n"
                f"<code>{eth_formatted}</code>{eva_txt}\n"
                f"━━━━━━━━━━━━━━━━━\n"
            )
            if hol:
                emoji = TYPE_EMOJI.get(hol["type"], "🔴")
                msg += f"\n{emoji} <b>የዛሬ በዓል፦</b> <b>{hol['am']}</b>\n"
                if hol.get("desc_am"):
                    msg += f"📖 <i>{hol['desc_am']}</i>\n"
        else:
            from app.handlers.calendar_view import ETH_MONTHS_EN
            e_month_name_en = ETH_MONTHS_EN[e_month - 1]
            e_day_name_en = EN_DAYS[now.weekday()]
            eth_formatted = f"🇪🇹 {e_day} - {e_month} - {e_year} | {e_day_name_en} - {e_month_name_en} - {e_day}"
            eva_txt = f" (Year of {evangelist['en']})" if evangelist else ""
            msg = (
                f"📅 <b>Today's Date Info</b>\n\n"
                f"<code>{greg_formatted}</code>\n"
                f"<code>{eth_formatted}</code>{eva_txt}\n"
                f"━━━━━━━━━━━━━━━━━\n"
            )
            if hol:
                emoji = TYPE_EMOJI.get(hol["type"], "🔴")
                msg += f"\n{emoji} <b>Today's Holiday:</b> <b>{hol['en']}</b>\n"
                if hol.get("desc_en"):
                    msg += f"📖 <i>{hol['desc_en']}</i>\n"

        # Embedded Action Buttons inside Today view
        if lang == "am":
            kb = [
                [InlineKeyboardButton("🗓 ቀን መቁጠሪያ ይክፈቱ (Open Calendar)", callback_data=f"cal:{tey}:{tem}")],
                [InlineKeyboardButton("📚 ስለ ቀን መቁጠሪያ (Calendar Info)", callback_data="show_calendar_info")],
                [InlineKeyboardButton("🎂 የዕድሜ ስሌት (Age Calculator)", callback_data="age_mode_start")]
            ]
        else:
            kb = [
                [InlineKeyboardButton("🗓 Open Interactive Calendar", callback_data=f"cal:{tey}:{tem}")],
                [InlineKeyboardButton("📚 Calendar History & Info", callback_data="show_calendar_info")],
                [InlineKeyboardButton("🎂 Age Calculator", callback_data="age_mode_start")]
            ]

        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await send_error(update, context, e, "today")

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id

        new_lang = "en" if get_lang(uid) == "am" else "am"
        set_lang(uid, new_lang)

        if new_lang == "am":
            msg = "✅ ቋንቋ ወደ አማርኛ ተቀይሯል"
        else:
            msg = "✅ Language changed to English"

        await update.message.reply_text(msg, reply_markup=get_menu(uid, new_lang))
        
    except Exception as e:
        await send_error(update, context, e, "lang")

async def calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides historical and logical information about the Ethiopian Calendar."""
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        track_activity(update, "/calendar")

        text = INFO_AM if lang == "am" else INFO_EN
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=get_share_keyboard(lang, context.bot.username, uid=uid))
    except Exception as e:
        await send_error(update, context, e, "calendar_command")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides information about the bot and developer."""
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        
        user_data = get_user_details(uid)
        ref_count = user_data[12] if user_data else 0

        if lang == "am":
            info_text = (
                "<b>ℹ️ ስለ ጳጉሜ ቦት (My Profile)</b>\n\n"
                "ጳጉሜ ቦት እጅግ ዘመናዊ እና ትክክለኛ የኢትዮጵያ ቀን መቁጠሪያ እና የቀን መቀየሪያ ቦት ነው።\n\n"
                f"👤 <b>የእርስዎ መረጃ፦</b>\n"
                f"🆔 <b>መለያ (ID)፦</b> <code>{uid}</code>\n"
                f"📊 <b>ያጋበዙት ሰዎች ብዛት፦</b> {ref_count}\n\n"
                "<b>📧 ኢሜይል:</b> support@pagumebot.com\n"
                "<b>🛠 የተሰራው፦</b> በ ShademT\n"
                "<b>📅 የተለቀቀው፦</b> ግንቦት 2018 ዓ.ም\n\n"
                "ለማንኛውም ጥያቄ ወይም አስተያየት ከታች ያለውን 'መልዕክት ላክ' የሚለውን ይጫኑ።"
            )
            btn_contact = "✍️ መልዕክት ላክ (Support)"
            btn_add = "➕ ቦቱን ወደ ግሩፕ አስገባ"
        else:
            info_text = (
                "<b>ℹ️ About Pagume Bot (My Profile)</b>\n\n"
                "Pagume Bot is the most advanced and precise Ethiopian Calendar & Date Converter on Telegram.\n\n"
                f"👤 <b>Your Info:</b>\n"
                f"🆔 <b>Account ID:</b> <code>{uid}</code>\n"
                f"📊 <b>Total Invited:</b> {ref_count} people\n\n"
                "<b>📧 Email:</b> support@pagumebot.com\n"
                "<b>🛠 Developed by:</b> ShademT\n"
                "<b>📅 Version:</b> May 2026\n\n"
                "For support, feedback, or inquiries, please use the button below or email us directly at support@pagumebot.com."
            )
            btn_contact = "✍️ Send Message to Admin"
            btn_add = "➕ Add Bot to Group"

        add_url = f"https://t.me/{context.bot.username}?startgroup=true"
        keyboard = [
            [InlineKeyboardButton(btn_contact, callback_data="contact_admin_request")],
            [InlineKeyboardButton(btn_add, url=add_url)]
        ]
        
        await update.message.reply_text(info_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
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
        
        user_data = get_user_details(uid)
        ref_count = user_data[12] if user_data else 0

        if lang == "am":
            text = (
                "<b>ጳጉሜ ቦት</b>\n"
                "<i>የኢትዮጵያ ቀን መቁጠሪያ እና ቀን መቀየሪያ ።</i>\n\n"
                "• <b>ትክክለኛ የቀን መቀየሪያ:</b> ከፈረንጅ ወደ ኢትዮጵያ\n"
                "• <b>የዕድሜ ስሌት:</b> ፈጣን እና ትክክለኛ\n"
                "• <b>በሁለት ቋንቋ:</b> አማርኛ እና እንግሊዝኛ\n\n"
                f"📊 <b>የእርስዎ ግብዣዎች፦</b> {ref_count} ሰዎች\n"
                f"🔗 <b>መጋበዣ ሊንክ፦</b> {share_link}"
            )
        else:
            text = (
                "<b>Pagume Bot</b>\n"
                "<i>The most advanced Ethiopian Calendar & Date Converter.</i>\n\n"
                "• <b>Precise Conversion:</b> Gregorian ↔ Ethiopian\n"
                "• <b>Age Calculator:</b> Fast & accurate\n"
                "• <b>Bilingual Support:</b> English & Amharic\n\n"
                f"📊 <b>Your Referrals:</b> {ref_count} people\n"
                f"🔗 <b>Referral Link:</b> {share_link}"
            )

        try:
            with open(INVITE_IMAGE_PATH, "rb") as photo:
                await update.message.reply_photo(
                    photo=photo, 
                    caption=text, 
                    parse_mode="HTML",
                    reply_markup=get_share_keyboard(lang, context.bot.username, uid=uid)
                )
        except Exception:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=get_share_keyboard(lang, context.bot.username, uid=uid))

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
        track_activity(update, "/help")

        if lang == "am":
            text = (
                "<b>🆘 የቦቱ እርዳታ እና መመሪያ</b>\n\n"
                "<b>👤 መሰረታዊ ትዕዛዞች:</b>\n"
                "• /start - ቦቱን ለመጀመር እና ለመቀስቀስ\n"
                "• /today - የዛሬን የኢትዮጵያ እና የፈረንጅ ቀን ለማየት\n"
                "• /calendar - ስለ ኢትዮጵያ ቀን መቁጠሪያ ጥልቅ መረጃ\n"
                "• /lang - ቋንቋ ለመቀየር (Amharic ↔ English)\n"
                "• /share - የግብዣ ሊንክ በመጠቀም ለጓደኞችዎ ለማጋራት\n"
                "• /about - ስለ ቦቱ መረጃ እና አድሚኑን ለማግኘት\n"
                "• /api - የራስዎን ፕሮግራም ለሚሰሩ (Developers) ቁልፍ ለመፍጠር\n\n"
                "<b>🛠 ተግባራት:</b>\n"
                "• <b>ቀን መቀየሪያ:</b> በዋናው ማውጫ ያሉትን ቁልፎች በመጫን ቀናትን ይቀይሩ።\n"
                "• <b>የዕድሜ ስሌት:</b> የተወለዱበትን ቀን በማስገባት ትክክለኛ ዕድሜዎን በኢትዮጵያ ወራት ይወቁ።"
            )
            
            if is_admin:
                text += (
                    "\n\n<b>👑 የአስተዳዳሪ (Admin) ትዕዛዞች:</b>\n"
                    "• /users - የተጠቃሚዎች ማኔጅመንት\n"
                    "  └>> <i>ጠቃሚ ምክር:</i> በአንድ ጊዜ 20 ተጠቃሚዎችን ማየት እና መፈለግ (Search) ይቻላል።\n"
                    "• /groups - ቦቱ ያለባቸው ግሩፖች ዝርዝር\n"
                    "• /broadcast - ለሁሉም የቦቱ ተጠቃሚዎች መልዕክት መላኪያ\n"
                    "• /api_stats - የኤፒአይ አጠቃቀም ስታቲስቲክስ\n"
                    "• /send_msg - ለተጠቃሚ በID ወይም በUsername ቀጥታ መልዕክት መላኪያ\n"
                    "• /block / /unblock - ተጠቃሚን ለማገድ ወይም ለማንሳት\n"
                    "• /leavegroup - ቦቱን ከግሩፕ ለማስወጣት"
                )
                
                if is_super:
                    text += (
                        "\n\n<b>🛡️ የሱፐር-አድሚን (Super-Admin) ትዕዛዞች:</b>\n"
                        "• /addadmin - አዲስ አስተዳዳሪ ለመመደብ\n"
                        "• /deladmin - አስተዳዳሪን ለመሰረዝ\n"
                        "• /listadmins - የአስተዳዳሪዎች ዝርዝር"
                    )

        else:
            text = (
                "<b>🆘 Bot Help & Documentation</b>\n\n"
                "<b>👤 General Commands:</b>\n"
                "• /start - Initialize the bot\n"
                "• /today - Show current date (Gregorian & Ethiopian)\n"
                "• /calendar - Deep dive into Ethiopian Calendar logic\n"
                "• /lang - Toggle language (English ↔ Amharic)\n"
                "• /share - Get your referral link and invite friends\n"
                "• /about - Bot credits and contact support\n"
                "• /api - Developer API portal and keys\n\n"
                "<b>🛠 Core Features:</b>\n"
                "• <b>Date Conversion:</b> Use menu buttons for seamless conversion flows.\n"
                "• <b>Age Calculator:</b> Get your precise age in Ethiopian months."
            )
            
            if is_admin:
                text += (
                    "\n\n<b>👑 Administrator Commands:</b>\n"
                    "• /users - Detailed User Dashboard\n"
                    "  └>> <i>Tip:</i> Supports search and sorting. Shows 20 users per page.\n"
                    "• /groups - Track bot installations in groups\n"
                    "• /broadcast - Send announcement to all users/groups\n"
                    "• /api_stats - API usage logs and management\n"
                    "• /send_msg - Direct message users by ID/Username\n"
                    "• /block / /unblock - Access control management\n"
                    "• /leavegroup - Force bot to leave a specific chat"
                )
                
                if is_super:
                    text += (
                        "\n\n<b>🛡️ Super-Admin Privileges:</b>\n"
                        "• /addadmin - Grant admin permissions\n"
                        "• /deladmin - Revoke admin permissions\n"
                        "• /listadmins - View current admin roster"
                    )

        await update.message.reply_text(text, parse_mode="HTML")

    except Exception as e:
        await send_error(update, context, e, "help_command")
