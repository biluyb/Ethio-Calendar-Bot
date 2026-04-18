import os
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, BotCommand
from app.db import register_user, get_lang, is_admin_db, get_admins_db, is_blocked_db, register_group
from app.config import ADMIN_IDS

# Constants
REDIRECT_IMAGE_URL = "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=1000&auto=format&fit=crop"
INVITE_IMAGE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "invite.jpg")

EN_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
EN_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

AM_DAYS = ["ሰኞ", "ማክሰኞ", "ረቡዕ", "ሐሙስ", "አርብ", "ቅዳሜ", "እሁድ"]
AM_MONTHS = ["መስከረም", "ጥቅምት", "ኅዳር", "ታኅሣሥ", "ጥር", "የካቲት", "መጋቢት", "ሚያዝያ", "ግንቦት", "ሰኔ", "ሐምሌ", "ነሐሴ", "ጳጉሜ"]

# Commands
USER_CMDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("lang", "Change language"),
    BotCommand("info", "Information about the calendar"),
    BotCommand("about", "Bot info & Contact Admin"),
    BotCommand("api", "Generate developer API key"),
    BotCommand("share", "Invite friends"),
    BotCommand("help", "How to use the bot")
]

ADMIN_CMDS = USER_CMDS + [
    BotCommand("users", "User dashboard"),
    BotCommand("groups", "List groups the bot is in"),
    BotCommand("broadcast", "Send message to all users"),
    BotCommand("api_stats", "API usage statistics and management"),
    BotCommand("send_msg", "Send DM to a user by ID or username"),
    BotCommand("block", "Block a user or group"),
    BotCommand("unblock", "Unblock a user or group"),
    BotCommand("leavegroup", "Force bot to leave a group")
]

SUPER_ADMIN_CMDS = ADMIN_CMDS + [
    BotCommand("addadmin", "Add new admin"),
    BotCommand("deladmin", "Remove admin"),
    BotCommand("listadmins", "List all admins")
]

# Helpers
def track_activity(update: Update, command_name: str = None) -> bool:
    user = update.effective_user
    if user:
        last_cmd = command_name
        if not last_cmd:
            if update.message and update.message.text: last_cmd = update.message.text[:50]
            elif update.callback_query: last_cmd = f"Button: {update.callback_query.data[:30]}"
            else: last_cmd = "Interaction"
        return register_user(user.id, user.username or str(user.id), full_name=user.full_name, last_command=last_cmd)
    return False

def get_menu(uid, lang):
    is_admin = is_admin_db(uid) or uid in ADMIN_IDS
    if lang == "am":
        kb = [["📅 ከፈረንጅ ወደ ኢትዮጵያ", "📆 ከኢትዮጵያ ወደ ፈረንጅ"], ["📅 ዛሬ", "🎂 የዕድሜ ስሌት"], ["🔐 ኤፒአይ (Developer)", "🌐 ቋንቋ"], ["🤝 ጓደኞችን ይጋብዙ", "ℹ️ ስለ ቦቱ እና እርዳታ"]]
        if is_admin:
            kb.append(["📢 መልዕክት ማስተላለፊያ (Broadcast)"])
            kb.append(["📊 ኤፒአይ ስታቲስቲክስ", "👥 ተጠቃሚዎች"])
    else:
        kb = [["📅 Gregorian ➜ Ethiopian", "📆 Ethiopian ➜ Gregorian"], ["📅 Today", "🎂 Age Calculator"], ["🔐 API (Developer)", "🌐 Language"], ["🤝 Invite Friends", "ℹ️ About & Support"]]
        if is_admin:
            kb.append(["📢 Broadcast Message"])
            kb.append(["📊 API Stats", "👥 Users"])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

async def notify_admin(context, error_text):
    admins = get_admins_db()
    all_notifiable = set(admins) | set(ADMIN_IDS)
    for admin_id in all_notifiable:
        try:
            await context.bot.send_message(chat_id=admin_id, text=f"🚨 <b>BOT ALERT</b>\n\n{error_text}", parse_mode="HTML")
        except: pass

async def send_error(update, context, error, func_name, user_msg=None):
    uid = update.effective_user.id if update.effective_user else "Unknown"
    uname = update.effective_user.username if update.effective_user else "Unknown"
    report = format_error_report(error, func_name, f"@{uname} ({uid})")
    if report: await notify_admin(context, report)
    try:
        if not user_msg:
            lang = get_lang(uid) if isinstance(uid, int) else "en"
            user_msg = "⚠️ An unexpected error occurred." if lang == "en" else "⚠️ ያልተጠበቀ ስህተት አጋጥሟል።"
        if update.message: await update.message.reply_text(user_msg)
        elif update.callback_query: await update.callback_query.answer(user_msg, show_alert=True)
    except: pass

def format_error_report(error, func_name, user_info=None):
    err_str = str(error)
    if "Message is not modified" in err_str: return None
    category = "Logic Bug"
    if "Connect" in err_str: category = "Network/API"
    elif "database" in err_str.lower(): category = "Database"
    report = f"🏷 <b>Category:</b> {category}\n📍 <b>Function:</b> <code>{func_name}</code>\n"
    if user_info: report += f"👤 <b>User:</b> {user_info}\n"
    report += f"❌ <b>Detail:</b> <code>{err_str[:150]}</code>"
    return report

def track_group(update: Update):
    chat = update.effective_chat
    if chat and chat.type in ["group", "supergroup"]:
        register_group(chat.id, chat.title)

async def check_blocked(update: Update):
    if not update or not update.effective_chat: return False
    return is_blocked_db(update.effective_chat.id)
