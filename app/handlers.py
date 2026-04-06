from app.db import get_all_users, search_users
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from datetime import datetime, timedelta, date
import calendar

from app.db import register_user, set_lang, get_lang, save_history, get_history
from app.utils import eth_to_greg, greg_to_eth
from app.texts import INFO_EN, INFO_AM
from app.config import ADMIN_ID

# ================== ERROR NOTIFIER==================


async def notify_admin(context, error_text):
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🚨 BOT ERROR:\n\n{error_text}"
        )
    except Exception as e:
        print("Admin notify failed:", e)

# ================== DAY & MONTH ==================

EN_DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
EN_MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]

AM_DAYS = ["ሰኞ","ማክሰኞ","ረቡዕ","ሐሙስ","አርብ","ቅዳሜ","እሁድ"]
AM_MONTHS = ["መስከረም","ጥቅምት","ኅዳር","ታኅሣሥ","ጥር","የካቲት","መጋቢት","ሚያዝያ","ግንቦት","ሰኔ","ሐምሌ","ነሐሴ","ጳጉሜ"]

# ================== users ==================
async def send_users_page(update: Update, query: str, page: int):
    if query:
        users_list = search_users(query)
    else:
        users_list = get_all_users()
        
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
    msg += f"📄 Page {page+1} of {total_pages}\n\n"
    
    msg += "\n".join([f"• <code>{u[0]}</code> - {u[1]}" for u in display_users])
    
    # Buttons
    buttons = []
    cb_prefix = f"users_pg_{query}_" if query else "users_pg__"
    
    # Note: Callback data length limit is 64 bytes. If search queries are too long, this might fail!
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"{cb_prefix}{page-1}"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"{cb_prefix}{page+1}"))
        
    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None
    
    if update.message:
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)


async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Restrict to Admin
    uid = update.effective_user.id
    if str(uid) != str(ADMIN_ID):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    query = " ".join(context.args) if context.args else ""
    await send_users_page(update, query, page=0)


async def users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_obj = update.callback_query
    uid = update.effective_user.id
    if str(uid) != str(ADMIN_ID):
        await query_obj.answer("Unauthorized", show_alert=True)
        return
        
    data = query_obj.data  
    # data format: users_pg_{search_term}_{page}
    data_content = data[len("users_pg_"):]
    parts = data_content.rsplit("_", 1) 
    search_term = parts[0]
    page = int(parts[1])
    
    await send_users_page(update, search_term, page)
    await query_obj.answer()

# ================== KEYBOARD ==================

def menu(lang):
    if lang == "am":
        return ReplyKeyboardMarkup([
            ["📅 ከፈረንጅ ወደ ኢትዮጵያ", "📆 ከኢትዮጵያ ወደ ፈረንጅ"],
            ["📆 ዛሬ", "📜 ታሪክ"],
            ["🌐 ቋንቋ", "ℹ️ መረጃ"]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            ["📅 Gregorian ➜ Ethiopian", "📆 Ethiopian ➜ Gregorian"],
            ["📆 Today", "📜 History"],
            ["🌐 Language", "ℹ️ Info"]
        ], resize_keyboard=True)
        
# ================== START ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        uid = user.id

        username = user.username or user.full_name or str(uid)
        register_user(uid, username)

        lang = get_lang(uid)

        if lang == "am":
            text = "📅 እንኳን ደህና መጡ\n\nአማራጭ ይምረጡ:"
        else:
            text = "📅 Welcome to Ethio Date Converter\n\nSelect option:"

        await update.message.reply_text(text, reply_markup=menu(lang))
    except Exception as e:
        await send_error(update, context, e, "start")   

    # ================== TODAY ==================

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)

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
        msg = f"Today \n\n📅 {g_year} - {g_month:02} - {g_day:02} | {g_day_name}, {g_month_name} - {g_year}\n"
        msg += f"📆 {e_day} - {e_month} - {e_year} | {e_day_name} - {e_month_name} - {e_day}"
    elif lang == "am":
        msg = f"ዛሬ \n\n📅 {g_year} - {g_month:02} - {g_day:02} | {g_day_name}, {g_month_name} - {g_year}\n"
        msg += f"📆 {e_day} - {e_month} - {e_year} | {e_day_name} - {e_month_name} - {e_day}"

    await update.message.reply_text(msg, reply_markup=menu(lang))

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




# ================== HISTORY ==================

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)

        hist = get_history(uid)

        if not hist:
            msg = "ምንም ታሪክ የለም" if lang=="am" else "No history"
        else:
            msg = "\n".join(hist[-10:])

        await update.message.reply_text(msg, reply_markup=menu(lang))
        

    except Exception as e:
        await send_error(update, context, e, "history")

# ================== HANDLE ==================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        text = update.message.text.strip()
        uid = update.effective_user.id
        text = update.message.text.strip()
        lang = get_lang(uid)
        

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

        if text in ["ℹ️ Info","ℹ️ መረጃ"]:
            return await info(update, context)

        if text in ["📜 History","📜 ታሪክ"]:
            return await history(update, context)

        # ---------- MODES ----------
        if text in ["📅 Gregorian ➜ Ethiopian","📅 ከፈረንጅ ወደ ኢትዮጵያ"]:
            context.user_data["mode"] = "g2e"
            msg = "Enter date DD/MM/YYYY \n\n example: 21/12/2022" if lang=="en" else "ቀን/ወር/ዓመት ያስገቡ\n\n ለምሳሌ: 21/12/2012"
            return await update.message.reply_text(msg)

        if text in ["📆 Ethiopian ➜ Gregorian","📆 ከኢትዮጵያ ወደ ፈረንጅ"]:
            context.user_data["mode"] = "e2g"
            msg = "Enter date DD/MM/YYYY \n\n example: 21/12/2022" if lang=="en" else "ቀን/ወር/ዓመት ያስገቡ \n\n ለምሳሌ: 21/12/2012"
            return await update.message.reply_text(msg)

        # ---------- PROCESS INPUT ----------
        if "mode" not in context.user_data:
            return

        try:
            d, m, y = map(int, text.replace("-", "/").split("/"))
        except:
            msg = "❌ Invalid format" if lang=="en" else "❌ ትክክለኛ ያልሆነ የቀን አጻጻፍ. እባክዎ ትክክለኛውን የቀን አጻጻፍ ያስገቡ"
            return await update.message.reply_text(msg)

        # ---------- CONVERSION ----------
        if context.user_data["mode"] == "g2e":
            ed, em, ey = greg_to_eth(d, m, y)
            wk_day = datetime(y, m, d).weekday()

            msg = f"📅 {y} - {m:02} - {d:02} || {EN_DAYS[wk_day]}, {EN_MONTHS[m-1]} - {y}\n"
            msg += f"📆 {ed} - {em} - {ey} || {AM_DAYS[wk_day]} - {AM_MONTHS[em-1]} - {ed} - {ey}"
        else:
            gd, gm, gy = eth_to_greg(d, m, y)
            wk_day = datetime(gy, gm, gd).weekday()

            msg = f"📅 {gy} - {gm:02} - {gd:02} || {EN_DAYS[wk_day]}, {EN_MONTHS[gm-1]} - {gy}\n"
            msg += f"📆 {d} - {m} - {y} || {AM_DAYS[wk_day]} - {AM_MONTHS[m-1]} - {d} - {y}"

        save_history(uid, msg)
        await update.message.reply_text(msg, reply_markup=menu(lang))
    
    
    #except Exception as e:
     #   await send_error(update, context, e, "handle")
        
    except Exception as e:
        error_msg = f"Handle Error:\n{str(e)}"
        print(error_msg)

        await notify_admin(context, error_msg)

        await update.message.reply_text("❌ Something went wrong. Try again")
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
            text = " የቦት መረጃ\n\n በ ShademT የተሰራ\n \n email: \nbiluquick123@gmail.com\n  © May 2026"
        else:
            text = " Bot Information\n\nDeveloped by ShademT\n\n email: \n biluquick123@gmail.com\n   © May 2026"

        await update.message.reply_text(text)
    
    except Exception as e:
        await send_error(update, context, e, "bot_info")    
    


    # ERROR_MESSAGE
async def send_error(update, context, error, func_name):
    user = update.effective_user

    msg = f"""
    🚨 ERROR in {func_name}
    User: {user.username}
    ID: {user.id}

    Error:
    {str(error)}
    """

    print(msg)  # terminal log

    # optional: send to you (admin)
    # await context.bot.send_message(chat_id=YOUR_ID, text=msg)

    # send to user (safe message)
    await update.message.reply_text("❌ Something went wrong. Try again.")
