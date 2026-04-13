from app.db import get_all_users, search_users
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, BotCommand, BotCommandScopeChat
from telegram.ext import ContextTypes
from datetime import datetime, timedelta, date
import calendar
import html

from app.db import register_user, set_lang, get_lang, is_admin_db, get_admins_db, add_admin_db, remove_admin_db
from app.utils import eth_to_greg, greg_to_eth
from app.texts import INFO_EN, INFO_AM
from app.config import ADMIN_IDS

# ================== ERROR NOTIFIER==================


async def notify_admin(context, error_text):
    admins = get_admins_db()
    for admin_id in admins:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🚨 <b>BOT ALERT</b>\n\n{error_text}",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Admin {admin_id} notify failed:", e)

def format_error_report(error, func_name):
    err_str = str(error)
    category = "Unknown Error"
    recommendation = "Check code/logs."

    if "ConnectError" in err_str or "Timed out" in err_str or "Connection" in err_str:
        category = "Network/API"
        recommendation = "Check server internet or Telegram API status."
    elif "OperationalError" in err_str or "InterfaceError" in err_str or "database" in err_str.lower():
        category = "Database"
        recommendation = "Check Supabase/Postgres connection or secrets."
    elif "Message is not modified" in err_str:
        return None
    elif "Forbidden" in err_str or "blocked" in err_str.lower():
        category = "Bot Blocked"
        recommendation = "User blocked the bot. No action needed."
    elif "ValueError" in err_str or "TypeError" in err_str or "index" in err_str.lower():
        category = "Logic Bug"
        recommendation = "Check date conversion or data parsing logic."

    return f"🏷 <b>Category:</b> {category}\n📍 <b>Function:</b> <code>{func_name}</code>\n❌ <b>Detail:</b> <code>{err_str[:150]}</code>\n💡 <b>Rec:</b> {recommendation}"

# ================== DAY & MONTH ==================

EN_DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
EN_MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]

AM_DAYS = ["ሰኞ","ማክሰኞ","ረቡዕ","ሐሙስ","አርብ","ቅዳሜ","እሁድ"]
AM_MONTHS = ["መስከረም","ጥቅምት","ኅዳር","ታኅሣሥ","ጥር","የካቲት","መጋቢት","ሚያዝያ","ግንቦት","ሰኔ","ሐምሌ","ነሐሴ","ጳጉሜ"]

# ================== users ==================
# ================== users ==================
async def send_users_page(update: Update, query: str, page: int, sort_by: str = "last_active_at"):
    if query:
        users_list = search_users(query, sort_by=sort_by)
    else:
        # get_all_users already sorts by last_active_at DESC
        users_list = get_all_users()
        if sort_by == "joined_at":
            users_list = sorted(users_list, key=lambda x: x[3] if len(x)>3 else 0, reverse=True)
        
    count = len(users_list)
    
    if count == 0:
        text = "❌ No users found."
        if update.message:
            await update.message.reply_text(text)
        else:
            await update.callback_query.edit_message_text(text)
        return
    
    per_page = 10
    total_pages = (count + per_page - 1) // per_page
    if page >= total_pages:
        page = total_pages - 1
    if page < 0:
        page = 0
        
    start_idx = page * per_page
    end_idx = start_idx + per_page
    
    display_users = users_list[start_idx:end_idx]
    
    msg = f"👥 <b>Total Users:</b> {count}\n"
    if query:
        msg += f"🔍 <b>Search:</b> {query}\n"
    msg += f"📊 <b>Sort:</b> {'Most Active' if sort_by == 'last_active_at' else 'Newest'}\n"
    msg += f"📄 Page {page+1} of {total_pages}\n\n"
    
    for u in display_users:
        uid, uname, lang = u[0], u[1], u[2]
        # joined_at is index 3, last_active_at is index 4
        joined = u[3] if len(u) > 3 else "N/A"
        active = u[4] if len(u) > 4 else "N/A"
        
        # Format timestamps if they are strings (SQLite)
        if isinstance(active, str) and len(active) > 16: active = active[:16]
        
        msg += f"• <code>{uname}</code> - {uid}\n"
        msg += f"   └>> Active: {active}\n"
    
    # Buttons
    buttons = []
    # Shorten callback prefix to stay under 64 bytes
    # Format: u_{page}_{sort}_{query}
    q_part = query[:20] # Limit query length in callback
    
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"u:{page-1}:{sort_by}:{q_part}"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"u:{page+1}:{sort_by}:{q_part}"))
        
    sort_buttons = [
        InlineKeyboardButton("🔥 Activity", callback_data=f"u:0:last_active_at:{q_part}"),
        InlineKeyboardButton("🆕 Newest", callback_data=f"u:0:joined_at:{q_part}")
    ]
    
    keyboard = []
    if buttons: keyboard.append(buttons)
    keyboard.append(sort_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)
    else:
        try:
            await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)
        except Exception as e:
            # Handle "message is not modified" error
            if "Message is not modified" not in str(e):
                raise e


async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Restrict to Admin
    uid = update.effective_user.id
    if not is_admin_db(uid):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    query = " ".join(context.args) if context.args else ""
    await send_users_page(update, query, page=0)


async def users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_obj = update.callback_query
    uid = update.effective_user.id
    if not is_admin_db(uid):
        await query_obj.answer("Unauthorized", show_alert=True)
        return
        
    data = query_obj.data  
    # data format: u:{page}:{sort}:{query}
    parts = data.split(":", 3)
    page = int(parts[1])
    sort_by = parts[2]
    search_term = parts[3] if len(parts) > 3 else ""
    
    await send_users_page(update, search_term, page, sort_by=sort_by)
    await query_obj.answer()

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return

    if not context.args:
        await update.message.reply_text("Usage: /addadmin <user_id>")
        return

    try:
        target_id = int(context.args[0])
        add_admin_db(target_id)
        await update.message.reply_text(f"✅ User <code>{target_id}</code> has been promoted to Admin.", parse_mode="HTML")
        await refresh_user_commands(context.bot, target_id)
        
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Invalid ID.")

async def del_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return

    if not context.args:
        await update.message.reply_text("Usage: /deladmin <user_id>")
        return

    try:
        target_id = int(context.args[0])
        # Prevent removing self if it's the last admin
        if target_id in ADMIN_IDS:
             await update.message.reply_text("❌ Cannot remove primary admin.")
             return
             
        remove_admin_db(target_id)
        await update.message.reply_text(f"✅ User <code>{target_id}</code> is no longer an Admin.", parse_mode="HTML")
        await refresh_user_commands(context.bot, target_id)
        
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Invalid ID.")

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return

    admins = get_admins_db()
    # Also show hardcoded ones
    all_admins = set(admins) | set(ADMIN_IDS)
    
    msg = "👥 **Current Admins:**\n\n"
    for a in all_admins:
        status = "(Primary)" if a in ADMIN_IDS else "(Added)"
        msg += f"• <code>{a}</code> {status}\n"
        
    await update.message.reply_text(msg, parse_mode="HTML")


async def age_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = update.effective_user.id
    lang = get_lang(uid)
    
    data = query.data
    mode = data.replace("age_mode_", "")
    
    context.user_data["mode"] = f"age_calc_{mode}"
    
    if mode == "gc":
        msg = "Enter your birthdate in Gregorian \n(DD/MM/YYYY):\n\nExample: 21/12/2012" if lang == "en" else "የትውልድ ቀንዎን በፈረንጅ አቆጣጠር ያስገቡ \n(ቀን/ወር/ዓመት)፦\n\nለምሳሌ: 21/12/2012"
    else:
        msg = "Enter your birthdate in Ethiopian \n(DD/MM/YYYY):\n\nExample: 21/12/2012" if lang == "en" else "የትውልድ ቀንዎን በኢትዮጵያ አቆጣጠር ያስገቡ \n(ቀን/ወር/ዓመት)፦\n\nለምሳሌ: 21/12/2012"
        
    await query.message.reply_text(msg)
    await query.answer()

def calculate_age(birth_date, current_date):
    years = current_date.year - birth_date.year
    months = current_date.month - birth_date.month
    days = current_date.day - birth_date.day
    
    if days < 0:
        months -= 1
        # Get days in the previous month
        prev_month = (current_date.month - 2) % 12 + 1
        prev_year = current_date.year if current_date.month > 1 else current_date.year - 1
        _, days_in_prev = calendar.monthrange(prev_year, prev_month)
        days += days_in_prev
        
    if months < 0:
        years -= 1
        months += 12
        
    return years, months, days

# ================== KEYBOARD ==================

def menu(lang):
    if lang == "am":
        return ReplyKeyboardMarkup([
            ["📅 ከፈረንጅ ወደ ኢትዮጵያ", "📆 ከኢትዮጵያ ወደ ፈረንጅ"],
            ["📆 ዛሬ", "🎂 የዕድሜ ስሌት"],
            ["🌐 ቋንቋ", "📩 አድሚኑን ያግኙ"]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            ["📅 Gregorian ➜ Ethiopian", "📆 Ethiopian ➜ Gregorian"],
            ["📆 Today", "🎂 Age Calculator"],
            ["🌐 Language", "📩 Contact Admin"]
        ], resize_keyboard=True)
        
# ================== START ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        uid = user.id

        await update.message.chat.send_action(action="typing")

        username = user.username or user.full_name or str(uid)
        register_user(uid, username)

        lang = get_lang(uid)

        if lang == "am":
            text = "📅 እንኳን ደህና መጡ\n\nአማራጭ ይምረጡ:"
        else:
            text = "📅 Welcome to Ethio Date Converter\n\nSelect option:"

        await update.message.reply_text(text, reply_markup=menu(lang))
        
        # Refresh commands on start if role changed or just to ensure correctness
        await refresh_user_commands(context.bot, uid)
    except Exception as e:
        await send_error(update, context, e, "start")   

# ================== RBAC & COMMAND MENU ==================

USER_CMDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("lang", "Change language"),
    BotCommand("info", "Information about the calendar"),
    BotCommand("help", "How to use the bot")
]

ADMIN_CMDS = USER_CMDS + [
    BotCommand("users", "User dashboard"),
    BotCommand("listadmins", "List all admins")
]

SUPER_ADMIN_CMDS = ADMIN_CMDS + [
    BotCommand("addadmin", "Add new admin"),
    BotCommand("deladmin", "Remove admin")
]

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

# ================== TODAY ==================

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id
        await update.message.chat.send_action(action="typing")
        
        lang = get_lang(uid)
        username = update.effective_user.username or update.effective_user.full_name or str(uid)
        register_user(uid, username)

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

        await update.message.reply_text(msg, reply_markup=menu(lang))
    except Exception as e:
        await send_error(update, context, e, "today")

# ================== LANGUAGE ==================

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id

        new_lang = "am" if get_lang(uid) == "am" else "en"
        set_lang(uid, new_lang)

        if new_lang == "am":
            msg = "✅ ቋንቋ ወደ አማርኛ ተቀይሯል"
        else:
            msg = "✅ Language changed to English"

        await update.message.reply_text(msg, reply_markup=menu(new_lang))
        
    except Exception as e:
        await send_error(update, context, e, "lang")

# ================== INFO ==================

#async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
 #   uid = update.effective_user.id
  #  lang = get_lang(uid)

   # from app.texts import INFO_AM, INFO_EN

    #await update.message.reply_text(INFO_AM if lang=="am" else INFO_EN)



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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        
        if lang == "am":
            text = "<b>🆘 የቦቱ እርዳታ</b>\n\n"
            text += "/start - ቦቱን ለመጀመር\n"
            text += "/lang - ቋንቋ ለመቀየር\n"
            text += "/today - የዛሬን ቀን ለማየት\n"
            text += "/info - ስለ ቀን መቁጠሪያው ግንዛቤ\n"
            text += "/about - ስለ ቦቱ መረጃ (አድሚኑን ለማግኘት)\n"
            text += "/help - ይህንን የእርዳታ መልዕክት ለማሳየት\n"
            
            if is_admin_db(uid) or uid in ADMIN_IDS:
                text += "\n<b>👑 የአስተዳዳሪ ትዕዛዞች:</b>\n"
                text += "/users - ስለ ተጠቃሚዎች መረጃ\n"
                
                if uid in ADMIN_IDS:
                    text += "/addadmin - አዲስ አስተዳዳሪ ለመጨመር\n"
                    text += "/deladmin - አስተዳዳሪ ለመቀነስ\n"
                    text += "/listadmins - የአስተዳዳሪዎች ዝርዝር\n"

        else:
            text = "<b>🆘 Bot Help</b>\n\n"
            text += "/start - Start the bot\n"
            text += "/lang - Change language\n"
            text += "/today - Show today's date\n"
            text += "/info - Calendar information\n"
            text += "/about - Bot info (Contact Admin)\n"
            text += "/help - Show this help message\n"
            
            if is_admin_db(uid) or uid in ADMIN_IDS:
                text += "\n<b>👑 Admin Commands:</b>\n"
                text += "/users - User dashboard\n"
                
                if uid in ADMIN_IDS:
                    text += "/addadmin - Add new admin\n"
                    text += "/deladmin - Remove admin\n"
                    text += "/listadmins - List all admins\n"
                    


        await update.message.reply_text(text, parse_mode="HTML")

    except Exception as e:
        await send_error(update, context, e, "help_command")




# ================== HISTORY ==================


# ================== HANDLE ==================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        text = update.message.text.strip()
        uid = update.effective_user.id
        
        await update.message.chat.send_action(action="typing")
        
        text = update.message.text.strip()
        lang = get_lang(uid)
        register_user(uid, update.effective_user.username or update.effective_user.full_name)
        

    # =====================
    # LANGUAGE SELECTION FIX
    # =====================
        if text == "🇺🇸 English":
            context.user_data["lang"] = "en"
            set_lang(uid, "en")
            await update.message.reply_text(
            "✅ Language set to English\n\nSelect option:",
            reply_markup=menu("en")
            )
            return


        if text == "🇪🇹 አማርኛ":
            context.user_data["lang"] = "am"
            set_lang(uid, "am")
            await update.message.reply_text(
                "✅ ቋንቋ ወደ አማርኛ ተቀይሯል",
                reply_markup=menu("am")   # ✅ ADD THIS
            )
            return
        # ---------- BUTTONS ----------
        if text in ["📆 Today","📆 ዛሬ"]:
            return await today(update, context)

        if text in ["🌐 Language","🌐 ቋንቋ"]:
            #return await language(update, context)
            keyboard = [["🇺🇸 English", "🇪🇹 አማርኛ"]]

            await update.message.reply_text(
            "Choose language / ቋንቋ ይምረጡ",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return

        if text in ["📩 Contact Admin", "📩 አድሚኑን ያግኙ", "📩   መልዕክት ላክ"]:
            context.user_data["mode"] = "contact_admin"
            msg = "እባክዎን ለአድሚኑ መላክ የሚፈልጉትን መልዕክት ይጻፉ።" if lang == "am" else "Please type the message you want to send to the admin."
            return await update.message.reply_text(msg)

        if text in ["ℹ️ About", "ℹ️ ስለ ቦቱ"]:
            return await bot_info(update, context)

        if text in ["🎂 Age Calculator","🎂 የዕድሜ ስሌት"]:
            lang = get_lang(uid)
            msg = "Choose birthdate calendar:" if lang == "en" else "የልደት ቀን መቁጠሪያ ይምረጡ፦"
            keyboard = [
                [InlineKeyboardButton("🇺🇸 Gregorian", callback_data="age_mode_gc"), 
                 InlineKeyboardButton("🇪🇹 Ethiopian", callback_data="age_mode_et")]
            ]
            return await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

        # ---------- MODES ----------
        if text in ["📅 Gregorian ➜ Ethiopian","📅 ከፈረንጅ ወደ ኢትዮጵያ"]:
            context.user_data["mode"] = "g2e"
            msg = "Enter date DD/MM/YYYY\n\nExample: 21/12/2022" if lang == "en" else "ቀን/ወር/ዓመት ያስገቡ\n\nለምሳሌ: 21/12/2012"
            return await update.message.reply_text(msg)

        if text in ["📆 Ethiopian ➜ Gregorian","📆 ከኢትዮጵያ ወደ ፈረንጅ"]:
            context.user_data["mode"] = "e2g"
            msg = "Enter date DD/MM/YYYY\n\nExample: 21/12/2022" if lang == "en" else "ቀን/ወር/ዓመት ያስገቡ\n\nለምሳሌ: 21/12/2012"
            return await update.message.reply_text(msg)

        # ---------- PROCESS INPUT ----------
        if "mode" not in context.user_data:
            return

        mode = context.user_data["mode"]
        
        # Process contact admin message
        if mode == "contact_admin":
            return await handle_admin_contact_message(update, context)

        # Process admin reply to user
        if mode.startswith("rep_"):
            return await handle_admin_reply_to_user(update, context)

        try:
            d, m, y = map(int, text.replace("-", "/").split("/"))
        except:
            msg = "❌ Invalid format. Please use DD/MM/YYYY\n\nExample: 21/12/2022" if lang=="en" else "❌ ትክክለኛ ያልሆነ የቀን አጻጻፍ. እባክዎ ቀን/ወር/ዓመት በ ቁጥር ያስገቡ\n\nለምሳሌ: 21/12/2012"
            return await update.message.reply_text(msg)

        # ---------- CONVERSION & AGE ----------
        try:
            if mode == "g2e":
                ed, em, ey = greg_to_eth(d, m, y)
                wk_day = datetime(y, m, d).weekday()

                msg = f"📅 {y} - {m:02} - {d:02} || {EN_DAYS[wk_day]}, {EN_MONTHS[m-1]} - {y}\n"
                msg += f"📆 {ed} - {em} - {ey} || {AM_DAYS[wk_day]} - {AM_MONTHS[em-1]} - {ed} - {ey}"
                await update.message.reply_text(msg, reply_markup=menu(lang))

            elif mode == "e2g":
                gd, gm, gy = eth_to_greg(d, m, y)
                wk_day = datetime(gy, gm, gd).weekday()

                msg = f"📅 {gy} - {gm:02} - {gd:02} || {EN_DAYS[wk_day]}, {EN_MONTHS[gm-1]} - {gy}\n"
                msg += f"📆 {d} - {m} - {y} || {AM_DAYS[wk_day]} - {AM_MONTHS[m-1]} - {d} - {y}"
                await update.message.reply_text(msg, reply_markup=menu(lang))

            elif mode.startswith("age_calc_"):
                now = datetime.now()
                if mode == "age_calc_gc":
                    birth_date = datetime(y, m, d)
                    ed, em, ey = greg_to_eth(d, m, y)
                    wk_day = birth_date.weekday()
                    
                    gd, gm, gy = d, m, y
                else:
                    gd, gm, gy = eth_to_greg(d, m, y)
                    birth_date = datetime(gy, gm, gd)
                    ed, em, ey = d, m, y
                    wk_day = birth_date.weekday()

                years, months, days = calculate_age(birth_date, now)
                
                # Format according to user request
                msg = f"🇺🇸 {gd:02} - {gm:02} - {gy} | {EN_DAYS[wk_day]}, {EN_MONTHS[gm-1]} - {gd:02}\n"
                msg += f"🇪🇹 {ed:02} - {em:02} - {ey} | {AM_DAYS[wk_day]} - {AM_MONTHS[em-1]} - {ed:02}\n\n"
                
                msg += f"━━━━━━━━━━━━━━━━━\n"
                if lang == "en":
                    msg += f"🎂 <b>{years}</b> Years | <b>{months}</b> Months | <b>{days}</b> Days"
                else:
                    msg += f"🎂 <b>{years}</b> ዓመት | <b>{months}</b> ወር | <b>{days}</b> ቀን"

                await update.message.reply_text(msg, parse_mode="HTML", reply_markup=menu(lang))
                # Clear mode after calculation
                del context.user_data["mode"]
        except ValueError as e:
            user_msg = "❌ Invalid date. \nEnter date DD/MM/YYYY\n\nExample: 21/12/2022." if lang == "en" else "❌ ትክክለኛ ያልሆነ ቀን። እባክዎ በዚህ ቅርጽ ያስገቡ\nቀን/ወር/ዓመት\n\nለምሳሌ: 21/12/2012"
            await send_error(update, context, e, f"handle_{mode}", user_msg=user_msg)
    
    
    #except Exception as e:
     #   await send_error(update, context, e, "handle")
        
    except Exception as e:
        await send_error(update, context, e, "handle")
  #menu commands
async def lang(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [["🇺🇸 English", "🇪🇹 አማርኛ"]]

    await update.message.reply_text(
        "Choose language / ቋንቋ ይምረጡ",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    
async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)

        if lang == "am":
            text = " የቦት መረጃ\n\n በ ShademT የተሰራ\n \n  © May 2026"
            btn_text = "📩 አድሚኑን ያግኙ"
        else:
            text = " Bot Information\n\nDeveloped by ShademT\n\n   © May 2026"
            btn_text = "📩 Contact Admin"

        keyboard = [[InlineKeyboardButton(btn_text, callback_data="contact_admin_request")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    except Exception as e:
        await send_error(update, context, e, "bot_info")    

async def contact_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = update.effective_user.id
    lang = get_lang(uid)
    
    context.user_data["mode"] = "contact_admin"
    
    if lang == "am":
        msg = "እባክዎን ለአድሚኑ መላክ የሚፈልጉትን መልዕክት ይጻፉ።"
    else:
        msg = "Please type the message you want to send to the admin."
        
    await query.message.reply_text(msg)
    await query.answer()

async def handle_admin_contact_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        # Confirm to user first for immediate feedback
        if lang == "am":
            confirm = "✅ መልዕክትዎ ለአድሚኑ ተልኳል። እናመሰግናለን!"
        else:
            confirm = "✅ Your message has been sent to the admin. Thank you!"
            
        await update.message.reply_text(confirm, reply_markup=menu(lang))
        
        # Clear mode immediately
        if "mode" in context.user_data:
            del context.user_data["mode"]

        # Forward to all admins in the background
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
            except Exception as e:
                print(f"Failed to send to admin {admin_id}: {e}")
            
    except Exception as e:
        await send_error(update, context, e, "handle_admin_contact_message")

async def admin_reply_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = update.effective_user.id
    
    # Restrict to Admin
    if not is_admin_db(uid):
        await query.answer("Unauthorized", show_alert=True)
        return
        
    target_uid = query.data.replace("admin_reply_", "")
    context.user_data["mode"] = f"rep_{target_uid}"
    
    await query.message.reply_text(f"✍️ <b>Replying to User:</b> <code>{target_uid}</code>\n\nPlease type your message below:", parse_mode="HTML")
    await query.answer()

async def handle_admin_reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        # Clear mode
        if "mode" in context.user_data:
            del context.user_data["mode"]
            
    except Exception as e:
        await send_error(update, context, e, "handle_admin_reply_to_user")
    


    # ERROR_MESSAGE
async def send_error(update, context, error, func_name, user_msg=None):
    print(f"🛑 ERROR in {func_name}: {error}")
    
    report = format_error_report(error, func_name)
    if report:
        await notify_admin(context, report)

    # Safe user message
    if update and update.effective_message:
        try:
            final_msg = user_msg if user_msg else "❌ Something went wrong. Please try again."
            await update.effective_message.reply_text(final_msg)
        except:
            pass

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    
    if lang == "am":
        text = "❌ ያልታወቀ ትዕዛዝ። እባክዎ ከታች ያለውን ማውጫ ይጠቀሙ ወይም ለተጨማሪ መረጃ /info ይጫኑ።"
    else:
        text = "❌ Unknown command. Please use the menu below or type /info for help."
        
    await update.message.reply_text(text, reply_markup=menu(lang))
