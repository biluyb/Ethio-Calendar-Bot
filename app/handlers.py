"""
Command Handlers and Bot Logic for Ethiopian Calendar Bot.
Implements Date conversion, Age calculation, Referral tracking, and Admin dashboards.
Uses a centralized error reporting system (`send_error`) to notify maintainers of issues.
"""

import calendar
import html
import asyncio
import os
from datetime import datetime, timedelta, date

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, 
    BotCommand, 
    BotCommandScopeChat
)
from telegram.ext import ContextTypes

# Constants
REDIRECT_IMAGE_URL = "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=1000&auto=format&fit=crop"
INVITE_IMAGE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "invite.jpg")

# Local imports
from app.db import (
    register_user, 
    set_lang, 
    get_lang, 
    is_admin_db, 
    get_admins_db, 
    add_admin_db, 
    remove_admin_db,
    get_all_user_ids,
    get_all_users,
    register_group,
    get_all_group_ids, 
    search_users,
    get_user_count,
    get_referrers_count,
    get_top_referrers,
    get_user_by_id,
    get_user_by_username,
    block_entity_db,
    unblock_entity_db,
    is_blocked_db,
    get_user_details
)
from app.utils import eth_to_greg, greg_to_eth
from app.texts import INFO_EN, INFO_AM
from app.config import ADMIN_IDS, BOT_TOKEN

# ================== CONSTANTS ==================

EN_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
EN_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

AM_DAYS = ["ሰኞ", "ማክሰኞ", "ረቡዕ", "ሐሙስ", "አርብ", "ቅዳሜ", "እሁድ"]
AM_MONTHS = ["መስከረም", "ጥቅምት", "ኅዳር", "ታኅሣሥ", "ጥር", "የካቲት", "መጋቢት", "ሚያዝያ", "ግንቦት", "ሰኔ", "ሐምሌ", "ነሐሴ", "ጳጉሜ"]

# ================== RBAC & COMMAND SETS ==================

USER_CMDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("lang", "Change language"),
    BotCommand("info", "Information about the calendar"),
    BotCommand("share", "Invite friends"),
    BotCommand("help", "How to use the bot")
]

ADMIN_CMDS = USER_CMDS + [
    BotCommand("users", "User dashboard"),
    BotCommand("groups", "List groups the bot is in"),
    BotCommand("broadcast", "Send message to all users"),
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

# ================== ERROR NOTIFIER==================
async def notify_admin(context, error_text):
    """
    Internal utility to broadcast critical errors or alerts to all registered admins.
    """
    admins = get_admins_db()
    # Ensure primary admins are always notified even if not in DB
    all_notifiable = set(admins) | set(ADMIN_IDS)
    
    for admin_id in all_notifiable:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🚨 <b>BOT ALERT</b>\n\n{error_text}",
                parse_mode="HTML"
            )
        except Exception as e:
            # Silence notification errors to prevent infinite loops or cascading failures
            print(f"Admin {admin_id} notify failed: {e}")

async def send_error(update, context, error, func_name, user_msg=None):
    """
    Standardized error reporter. Captures stack trace details, categorizes the error,
    and notifies admins while providing a graceful response to the end user.
    """
    uid = update.effective_user.id if update.effective_user else "Unknown"
    uname = update.effective_user.username if update.effective_user else "Unknown"
    user_info = f"@{uname} ({uid})"
    
    report = format_error_report(error, func_name, user_info)
    if report:
        await notify_admin(context, report)
        
    # Provide a graceful fallback to the user
    try:
        if not user_msg:
            lang = get_lang(uid) if isinstance(uid, int) else "en"
            user_msg = "⚠️ An unexpected error occurred. Our team has been notified." if lang == "en" else "⚠️ ያልተጠበቀ ስህተት አጋጥሟል። ለቴክኒክ ቡድናችን አሳውቀናል።"
        
        if update.message:
            await update.message.reply_text(user_msg)
        elif update.callback_query:
            await update.callback_query.answer(user_msg, show_alert=True)
    except Exception:
        pass

def format_error_report(error, func_name, user_info=None):
    """
    Parses exception details into a human-readable HTML report for admins.
    Categorizes errors based on string patterns for quick triaging.
    """
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

    report = f"🏷 <b>Category:</b> {category}\n📍 <b>Function:</b> <code>{func_name}</code>\n"
    if user_info:
        report += f"👤 <b>User:</b> {user_info}\n"
    report += f"❌ <b>Detail:</b> <code>{str(err_str)[:150]}</code>\n💡 <b>Rec:</b> {recommendation}"
    return report

# ================== ADMIN TOOLS ==================
# ================== users ==================
async def send_users_page(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, page: int, sort_by: str = "last_active_at", order: str = "DESC"):
    """
    Core logic for the paginated user dashboard. 
    Fetches data from DB and constructs the visual report with interactive buttons.
    """
    try:
        q_part = query[:20] if query else ""
        per_page = 10
        keyboard = []
        
        # 1. Get total count from DB
        count = get_user_count(query if query else None, filter_blocked=(sort_by == "blocked"))
        
        if count == 0:
            text = "❌ No users found."
            if update.message:
                await update.message.reply_text(text)
            else:
                await update.callback_query.edit_message_text(text)
            return
        
        total_pages = (count + per_page - 1) // per_page
        if page >= total_pages:
            page = total_pages - 1
        if page < 0:
            page = 0
            
        offset = page * per_page
        
        # 2. Fetch only the required page from DB
        if query:
            display_users = search_users(query, sort_by=sort_by, order=order, limit=per_page, offset=offset)
        else:
            display_users = get_all_users(sort_by=sort_by, order=order, limit=per_page, offset=offset)
    
        sort_name = {
            'last_active_at': '🔥 Most Active',
            'joined_at': '🆕 Newest',
            'referrals': '🤝 Referrals',
            'blocked': '🚫 Blocked'
        }.get(sort_by, '🔥 Most Active')
        
        msg = f"👥 <b>Total Users:</b> {count}\n"
        if query:
            msg += f"🔍 <b>Search:</b> {query}\n"
        
        order_icon = "🔼" if order == "ASC" else "🔽"
        msg += f"📊 <b>View:</b> {sort_name} {order_icon}\n"
        msg += f"📄 Page {page+1} of {total_pages}\n\n"
        
        for user_data in display_users:
            # DB returns: (id, username, full_name, lang, joined_at, last_active_at, last_command, total_actions, referred_by, is_blocked, referral_count)
            uid, uname, fname, lang, joined, active, last_cmd, total_acts, ref_by, is_blocked, ref_count = user_data[:11]
            
            # Format timestamps if they are strings (SQLite)
            active_str = str(active)[:16]
            
            block_icon = "🚫 " if is_blocked else ""
            msg += f"• {block_icon}<b>{uname}</b> - <code>{uid}</code>\n"
            msg += f"   └>> Active: {active_str} | Actions: <b>{total_acts}</b>\n"
            
            # Add a button to view this specific user
            row_btns = [InlineKeyboardButton(f"👤 View {uname or uid}", callback_data=f"ud:{uid}:{page}:{sort_by}:{q_part}")]
            keyboard.append(row_btns)
        
        # Buttons
        buttons = []
        # Shorten callback prefix to stay under 64 bytes
        # Format: u_{page}_{sort}_{query}
        
        if isinstance(page, int) and page > 0:
            buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"u:{page-1}:{sort_by}:{order}:{q_part}"))
        if isinstance(page, int) and isinstance(total_pages, int) and page < total_pages - 1:
            buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"u:{page+1}:{sort_by}:{order}:{q_part}"))
            
        def get_sort_btn(label, target_sort, icon):
            # If current sort is this one, toggle order, otherwise default to DESC
            target_order = "ASC" if (sort_by == target_sort and order == "DESC") else "DESC"
            
            # Add icon if this is the active sort
            indicator = ""
            if sort_by == target_sort:
                indicator = " 🔼" if order == "ASC" else " 🔽"
            
            return InlineKeyboardButton(f"{icon}{label}{indicator}", callback_data=f"u:0:{target_sort}:{target_order}:{q_part}")

        sort_buttons = [
            [
                get_sort_btn("Activity", "last_active_at", "🔥 "),
                get_sort_btn("Newest", "joined_at", "🆕 ")
            ],
            [
                get_sort_btn("Referrals", "referrals", "🤝 "),
                get_sort_btn("Blocked", "blocked", "🚫 ")
            ]
        ]
        
        if buttons: keyboard.append(buttons)
        keyboard.extend(sort_buttons)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)
        else:
            try:
                await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)
            except Exception as e:
                # Handle "message is not modified" error gracefully
                if "Message is not modified" not in str(e):
                    raise e
    except Exception as e:
        await send_error(update, context, e, "send_users_page")

async def send_user_detail_view(update, context, target_uid, p_back=0, s_back="last_active_at", o_back="DESC", q_back=""):
    """Displays a comprehensive profile for a single user."""
    try:
        user_data = get_user_details(target_uid)
        if not user_data:
            await update.callback_query.answer("❌ User not found.", show_alert=True)
            return

        # (id, username, full_name, lang, joined_at, last_active_at, last_command, total_actions, referred_by, is_blocked, referral_count)
        uid, uname, fname, lang, joined, active, last_cmd, total_acts, ref_by, is_blocked, ref_count = user_data

        msg = f"👤 <b>User Profile: {html.escape(fname or uname or str(uid))}</b>\n"
        msg += f"━━━━━━━━━━━━━━━\n"
        msg += f"🆔 <b>ID:</b> <code>{uid}</code>\n"
        msg += f"📛 <b>Username:</b> @{uname if uname else '---'}\n"
        msg += f"🌍 <b>Language:</b> {lang.upper()}\n"
        msg += f"🗓️ <b>Joined:</b> {str(joined)[:16]}\n"
        msg += f"🔥 <b>Last Seen:</b> {str(active)[:16]}\n"
        msg += f"⌨️ <b>Last Action:</b> <code>{html.escape(last_cmd or '---')}</code>\n"
        msg += f"📊 <b>Total Actions:</b> <b>{total_acts}</b>\n"
        msg += f"🤝 <b>Referrals:</b> <b>{ref_count}</b>\n"
        msg += f"🛡️ <b>Referred By:</b> <code>{ref_by or '---'}</code>\n"
        msg += f"🚫 <b>Blocked:</b> {'Yes' if is_blocked else 'No'}\n"
        
        buttons = [
            [
                InlineKeyboardButton("📩 Send Message", callback_data=f"send_msg_init:{uid}"),
                InlineKeyboardButton("🚫 Block" if not is_blocked else "✅ Unblock", callback_data=f"toggle_block_user:{uid}:{p_back}:{s_back}:{o_back}:{q_back}")
            ],
            [InlineKeyboardButton("⬅️ Back to List", callback_data=f"u:{p_back}:{s_back}:{o_back}:{q_back}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        await send_error(update, context, e, "send_user_detail_view")

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to launch the user dashboard."""
    try:
        uid = update.effective_user.id
        if not is_admin_db(uid):
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return

        query = " ".join(context.args) if context.args else ""
        await send_users_page(update, context, query, page=0)
    except Exception as e:
        await send_error(update, context, e, "users")

async def users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles pagination and sorting button clicks for the user dashboard."""
    try:
        query_obj = update.callback_query
        uid = update.effective_user.id
        if not is_admin_db(uid):
            await query_obj.answer("Unauthorized", show_alert=True)
            return
            
        data = query_obj.data  
        
        # Handle User Detail View (ud:uid:p:s:o:q)
        if data.startswith("ud:"):
            parts = data.split(":", 6)
            target_uid = int(parts[1])
            p_back = int(parts[2])
            s_back = parts[3]
            o_back = parts[4]
            q_back = parts[5] if len(parts) > 5 else ""
            await send_user_detail_view(update, context, target_uid, p_back, s_back, o_back, q_back)
            await query_obj.answer()
            return
            
        # Handle Block Toggle (toggle_block_user:uid:p:s:o:q)
        if data.startswith("toggle_block_user:"):
            parts = data.split(":", 6)
            target_uid = int(parts[1])
            p_back = int(parts[2])
            s_back = parts[3]
            o_back = parts[4]
            q_back = parts[5] if len(parts) > 5 else ""
            
            # Toggle logic
            if is_blocked_db(target_uid):
                unblock_entity_db(target_uid)
                await query_obj.answer("✅ User Unblocked", show_alert=True)
            else:
                block_entity_db(target_uid)
                await query_obj.answer("🚫 User Blocked", show_alert=True)
            
            # Refresh detail view
            await send_user_detail_view(update, context, target_uid, p_back, s_back, o_back, q_back)
            return

        # Handle Direct Message Initialization (send_msg_init:uid)
        if data.startswith("send_msg_init:"):
            target_uid = int(data.split(":")[1])
            user_data = get_user_details(target_uid)
            target_name = user_data[1] or user_data[2] or str(target_uid) if user_data else str(target_uid)
            
            context.user_data["mode"] = "admin_dm_send"
            context.user_data["target_uid"] = target_uid
            context.user_data["target_name"] = target_name
            
            lang = get_lang(uid)
            msg = f"✍️ <b>Sending to:</b> {target_name} [<code>{target_uid}</code>]\n\nPlease type your message below:" if lang=="en" else f"✍️ <b>ለመላክ የተመረጠው፦</b> {target_name} [<code>{target_uid}</code>]\n\nእባክዎን መልዕክትዎን ከታች ይጻፉ፦"
            await query_obj.edit_message_text(msg, parse_mode="HTML")
            await query_obj.answer()
            return

        # Handle User List (u:p:s:o:q)
        parts = data.split(":", 4)
        page = int(parts[1])
        sort_by = parts[2]
        order = parts[3] if len(parts) > 3 else "DESC"
        search_term = parts[4] if len(parts) > 4 else ""
        
        await send_users_page(update, context, search_term, page, sort_by=sort_by, order=order)
        await query_obj.answer()
    except Exception as e:
        await send_error(update, context, e, "users_callback")


async def send_groups_page(update, context, page=0, query=None):
    """Helper to send or edit the groups paginated dashboard, supporting search."""
    try:
        from app.db import get_all_groups, get_group_count, search_groups
        per_page = 10
        count = get_group_count(query=query)
        total_pages = (count + per_page - 1) // per_page
        
        if total_pages == 0:
            msg = f"🚫 No groups found{f' for <b>{query}</b>' if query else ''}."
            if update.message:
                await update.message.reply_text(msg, parse_mode="HTML")
            else:
                await update.callback_query.edit_message_text(msg, parse_mode="HTML")
            return
            
        if page >= total_pages:
            page = total_pages - 1
        if page < 0:
            page = 0
            
        offset = page * per_page
        if query:
            display_groups = search_groups(query, limit=per_page, offset=offset)
        else:
            display_groups = get_all_groups(limit=per_page, offset=offset)
        
        msg = f"🏘️ <b>Total Groups:</b> {count}\n"
        if query:
            msg += f"🔍 <b>Search:</b> {query}\n"
        msg += f"📄 Page {page+1} of {total_pages}\n\n"
        
        for g_id, g_title, g_joined, g_blocked in display_groups:
            if isinstance(g_joined, str) and len(g_joined) > 16:
                g_joined = g_joined[:16]
            block_icon = "🚫 " if g_blocked else ""
            msg += f"• {block_icon}<code>{g_title}</code> - {g_id}\n"
            msg += f"   └>> Added: {g_joined}\n"
            
        # Buttons
        buttons = []
        q_part = query[:20] if query else ""
        
        if isinstance(page, int) and page > 0:
            buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"g:{page-1}:{q_part}"))
        if isinstance(page, int) and isinstance(total_pages, int) and page < total_pages - 1:
            buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"g:{page+1}:{q_part}"))
            
        keyboard = []
        if buttons: keyboard.append(buttons)
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        if update.message:
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)
        else:
            try:
                await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)
            except Exception as e:
                if "Message is not modified" not in str(e):
                    raise e
    except Exception as e:
        await send_error(update, context, e, "send_groups_page")

async def groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to list all groups the bot is in."""
    try:
        uid = update.effective_user.id
        if not is_admin_db(uid):
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return

        query = " ".join(context.args) if context.args else None
        await send_groups_page(update, context, page=0, query=query)
    except Exception as e:
        await send_error(update, context, e, "groups_command")

async def groups_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles pagination for the groups list."""
    try:
        query_obj = update.callback_query
        uid = update.effective_user.id
        if not is_admin_db(uid):
            await query_obj.answer("Unauthorized", show_alert=True)
            return
            
        data = query_obj.data  
        parts = data.split(":", 2)
        page = int(parts[1])
        query = parts[2] if len(parts) > 2 else None
        
        await send_groups_page(update, context, page, query=query)
        await query_obj.answer()
    except Exception as e:
        await send_error(update, context, e, "groups_callback")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super-Admin command to promote a user to Admin status."""
    try:
        uid = update.effective_user.id
        if uid not in ADMIN_IDS:
            return

        if not context.args:
            await update.message.reply_text("Usage: /addadmin <user_id>")
            return

        target_id_str = context.args[0]
        if not target_id_str.isdigit() and not (target_id_str.startswith("-") and target_id_str[1:].isdigit()):
            await update.message.reply_text("❌ Invalid ID. Please provide a numeric User ID.")
            return

        target_id = int(target_id_str)
        add_admin_db(target_id)
        await update.message.reply_text(f"✅ User <code>{target_id}</code> has been promoted to Admin.", parse_mode="HTML")
        await refresh_user_commands(context.bot, target_id)
    except Exception as e:
        await send_error(update, context, e, "add_admin")

async def del_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super-Admin command to revoke Admin status from a user."""
    try:
        uid = update.effective_user.id
        if uid not in ADMIN_IDS:
            return

        if not context.args:
            await update.message.reply_text("Usage: /deladmin <user_id>")
            return

        target_id_str = context.args[0]
        if not target_id_str.isdigit() and not (target_id_str.startswith("-") and target_id_str[1:].isdigit()):
             await update.message.reply_text("❌ Invalid ID.")
             return

        target_id = int(target_id_str)
        if target_id in ADMIN_IDS:
             await update.message.reply_text("❌ Cannot remove primary admin.")
             return
             
        remove_admin_db(target_id)
        await update.message.reply_text(f"✅ User <code>{target_id}</code> is no longer an Admin.", parse_mode="HTML")
        await refresh_user_commands(context.bot, target_id)
    except Exception as e:
        await send_error(update, context, e, "del_admin")

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to list all users with administrative privileges."""
    try:
        uid = update.effective_user.id
        if uid not in ADMIN_IDS:
            return

        admins = get_admins_db()
        # Also show hardcoded ones
        all_admins = set(admins) | set(ADMIN_IDS)
        
        msg = "👥 <b>Current Admins:</b>\n\n"
        for a in all_admins:
            status = "(Primary)" if a in ADMIN_IDS else "(Added)"
            msg += f"• <code>{a}</code> {status}\n"
            
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        await send_error(update, context, e, "list_admins")

async def age_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the selection of Gregorian vs Ethiopian birthdate input."""
    try:
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
    except Exception as e:
        await send_error(update, context, e, "age_mode_callback")

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
def get_menu(uid, lang):
    """
    Returns a role-aware reply keyboard with a modern, emoji-rich layout.
    """
    is_admin = is_admin_db(uid) or uid in ADMIN_IDS
    
    if lang == "am":
        kb = [
            ["📅 ከፈረንጅ ወደ ኢትዮጵያ", "📆 ከኢትዮጵያ ወደ ፈረንጅ"],
            ["📅 ዛሬ", "🎂 የዕድሜ ስሌት"],
            ["🌐 ቋንቋ", "🤝 ጓደኞችን ይጋብዙ"],
            ["📩 አድሚኑን ያግኙ"]
        ]
        if is_admin:
            kb.append(["📢 መልዕክት ማስተላለፊያ (Broadcast)"])
    else:
        kb = [
            ["📅 Gregorian ➜ Ethiopian", "📆 Ethiopian ➜ Gregorian"],
            ["📅 Today", "🎂 Age Calculator"],
            ["🌐 Language", "🤝 Invite Friends"],
            ["📩 Contact Admin"]
        ]
        if is_admin:
            kb.append(["📢 Broadcast Message"])
            
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)
        
async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to block a user or group."""
    try:
        uid = update.effective_user.id
        if not is_admin_db(uid):
            return

        if not context.args:
            await update.message.reply_text("Usage: /block <id>")
            return

        target_id = int(context.args[0])
        block_entity_db(target_id)
        await update.message.reply_text(f"✅ ID <code>{target_id}</code> has been blocked.", parse_mode="HTML")
    except Exception as e:
        await send_error(update, context, e, "block_command")

async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to unblock a user or group."""
    try:
        uid = update.effective_user.id
        if not is_admin_db(uid):
            return

        if not context.args:
            await update.message.reply_text("Usage: /unblock <id>")
            return

        target_id = int(context.args[0])
        unblock_entity_db(target_id)
        await update.message.reply_text(f"✅ ID <code>{target_id}</code> has been unblocked.", parse_mode="HTML")
    except Exception as e:
        await send_error(update, context, e, "unblock_command")

async def leavegroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to force the bot to leave a specified group."""
    try:
        uid = update.effective_user.id
        if not is_admin_db(uid):
            return

        if not context.args:
            await update.message.reply_text(
                "Usage: /leavegroup <group_id>\n\nUse /groups to find group IDs."
            )
            return

        try:
            group_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid group ID. Must be a number.")
            return

        try:
            await context.bot.leave_chat(chat_id=group_id)
            await update.message.reply_text(
                f"✅ Bot has left group <code>{group_id}</code>.", parse_mode="HTML"
            )
        except Exception as leave_err:
            await update.message.reply_text(
                f"❌ Could not leave group <code>{group_id}</code>: {leave_err}", parse_mode="HTML"
            )
    except Exception as e:
        await send_error(update, context, e, "leavegroup_command")

async def check_blocked(update: Update):
    """Checks if the user or chat is blocked. Returns True if blocked."""
    if not update or not update.effective_chat:
        return False
    
    cid = update.effective_chat.id
    if is_blocked_db(cid):
        # Silently ignore blocked users/chats to avoid bot spamming
        return True
    return False

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update): return
    try:
        # Redirect group chat messages to DM before any other processing
        if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
            uid = update.effective_user.id if update.effective_user else None
            lang = get_lang(uid) if uid else "en"
            track_group(update)
            if uid: register_user(uid, update.effective_user.username or str(uid), full_name=update.effective_user.full_name, last_command="/start (Group)")
            
            bot_username = context.bot.username
            dm_url = f"https://t.me/{bot_username}?start=from_group"
            btn_text = "▶️ ቦቱን ክፈት" if lang == "am" else "▶️ Open Bot"
            keyboard = [[InlineKeyboardButton(btn_text, url=dm_url)]]
            msg = "\n\n  📩 ቦቱን ለመጠቀም ወደ DM ይሂዱ።\n\n @pagumebot\n" if lang == "am" else "\n\n📩 Please use this bot in a private DM for the best experience.\n\n @pagumebot"
            
            try:
                with open(INVITE_IMAGE_PATH, "rb") as photo:
                    await update.message.reply_photo(
                        photo=photo, 
                        caption=msg, 
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            except Exception:
                await update.message.reply_photo(
                    photo=REDIRECT_IMAGE_URL, 
                    caption=msg, 
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            return

        user = update.effective_user
        uid = user.id

        await update.message.chat.send_action(action="typing")

        username = user.username or user.full_name or str(uid)
        
        # Check for referral payload in /start
        referred_by = None
        if context.args and context.args[0].isdigit():
            referrer_id = int(context.args[0])
            if referrer_id != uid: # Cannot refer self
                referred_by = referrer_id
        
        is_new = register_user(uid, username, full_name=user.full_name, last_command="/start", referred_by=referred_by)
        track_group(update)

        # Notify referrer if this is a new registration
        if is_new and referred_by:
            try:
                ref_lang = get_lang(referred_by)
                if ref_lang == "am":
                    notif = f"🎉 <b>እንኳን ደስ አለዎት!</b>\n\n<b>{username}</b> በእርስዎ ግብዣ መሠረት ቦቱን ተቀላቅሏል።"
                else:
                    notif = f"🎉 <b>New Referral!</b>\n\n<b>{username}</b> has joined the bot using your invite link."
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

# ================== UTILS ==================
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

        await update.message.reply_text(msg, reply_markup=get_menu(uid, lang))
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

        await update.message.reply_text(msg, reply_markup=get_menu(uid, new_lang))
        
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
                
                if is_super:
                    text += "\n<b>🛡️ Super-Admin Commands:</b>\n"
                    text += "/addadmin - Add new admin\n"
                    text += "/deladmin - Remove admin\n"
                    text += "/listadmins - List all admins\n"
                    


        await update.message.reply_text(text, parse_mode="HTML")

    except Exception as e:
        await send_error(update, context, e, "help_command")

def track_group(update: Update):
    chat = update.effective_chat
    if chat and chat.type in ["group", "supergroup"]:
        register_group(chat.id, chat.title)

# ================== HANDLE ==================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update): return
    
    user = update.effective_user
    if user:
        register_user(user.id, user.username or str(user.id), full_name=user.full_name, last_command=update.message.text[:50] if update.message and update.message.text else "Interaction")

    try:
        # Redirect group chat messages to DM before any other processing
        if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
            if update.message and update.message.text:
                uid = update.effective_user.id if update.effective_user else None
                lang = get_lang(uid) if uid else "en"
                track_group(update)
                register_user(uid, update.effective_user.username or update.effective_user.full_name) if uid else None
                bot_username = context.bot.username
                dm_url = f"https://t.me/{bot_username}?start=from_group"
                btn_text = "▶️ ቦቱን ክፈት" if lang == "am" else "▶️ Open Bot"
                keyboard = [[InlineKeyboardButton(btn_text, url=dm_url)]]
                msg = "📩 ቦቱን ለመጠቀም ወደ ቀጥታ መልዕክት (DM) ይሂዱ።" if lang == "am" else "📩 Please use this bot in a private DM for the best experience."
                
                try:
                    with open(INVITE_IMAGE_PATH, "rb") as photo:
                        await update.message.reply_photo(
                            photo=photo, 
                            caption=msg, 
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                except Exception:
                    await update.message.reply_photo(
                        photo=REDIRECT_IMAGE_URL, 
                        caption=msg, 
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
        register_user(uid, update.effective_user.username or update.effective_user.full_name)
        

    # =====================
    # MAIN HANDLER LOGIC
    # =====================
        # Pre-process common data
        user = update.effective_user
        if not user:
            return
            
        username = user.username or user.full_name or "Unknown"
        register_user(uid, str(username))

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
            return await handle_admin_dm_send(update, context)

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
                # Fallback generic date error
                user_msg = (
                    "❌ Invalid date range. \nEnter date DD/MM/YYYY\n\nExample: 21/12/2022." 
                    if lang == "en" else 
                    "❌ ትክክለኛ ያልሆነ ቀን። እባክዎ በዚህ ቅርጽ ያስገቡ\nቀን/ወር/ዓመት\n\nለምሳሌ: 21/12/2012"
                )
                
            await update.message.reply_text(user_msg)
            
    except Exception as e:
        await send_error(update, context, e, "handle")

# ================== SUB-HANDLERS (MODULAR) ==================
async def process_menu_commands(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, uid: int, lang: str) -> bool:
    """Processes menu button clicks. Returns True if handled."""
    # Language Selection Buttons
    if text == "🇺🇸 English":
        set_lang(uid, "en")
        await update.message.reply_text("✅ Language set to English", reply_markup=get_menu(uid, "en"))
        return True

    if text == "🇪🇹 አማርኛ":
        set_lang(uid, "am")
        await update.message.reply_text("✅ ቋንቋ ወደ አማርኛ ተቀይሯል", reply_markup=get_menu(uid, "am"))
        return True

    # Special Command Handling
    if text in ["📅 Today", "📅 ዛሬ"]:
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

    # Broadcast Menu Button
    if text in ["📢 Broadcast Message", "📢 መልዕክት ማስተላለፊያ (Broadcast)"]:
        if is_admin_db(uid) or uid in ADMIN_IDS:
            await update.message.reply_text("Usage: /broadcast <message>\n\nOr just type your message with the command.")
        return True

    return False

async def process_g2e(update: Update, context: ContextTypes.DEFAULT_TYPE, d: int, m: int, y: int, lang: str):
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
        user_msg = (
            f"❌ Invalid date: {err_msg}\n\nExample: 21/12/2022" if lang == "en" else 
            f"❌ የተሳሳተ ቀን: {err_msg}\n\nለምሳሌ: 21/12/2012"
        )
        if "day is out of range for month" in err_msg:
             user_msg = (
                "❌ The day you entered is not valid for that month." if lang == "en" else 
                "❌ ያስገቡት ቀን ለዛ ወር ትክክል አይደለም።"
            )
        elif "month must be in 1..12" in err_msg.lower():
             user_msg = (
                "❌ Month must be between 1 and 12." if lang == "en" else 
                "❌ ወር ከ 1 እስከ 12 መሆን አለበት።"
            )
        await update.message.reply_text(user_msg)
        # Don't pop mode so they can try again
    except Exception as e:
        await send_error(update, context, e, "process_g2e")

async def share_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates and sends a unique referral link for the user."""
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        bot_me = await context.bot.get_me()
        bot_username = bot_me.username
        share_link = f"https://t.me/{bot_username}?start={uid}"
        
        if lang == "am":
            text = f"<b>የኢትዮጵያ ቀን መለወጫ ቦት</b>\n\nይህንን ቦት ለጓደኞችዎ እንዲጠቀሙ ይጋብዙ! ቦቱን ተጠቅመው የፈረንጅን ቀን ወደ ኢትዮጵያ፣ የኢትዮጵያን ደግሞ ወደ ፈረንጅ መቀየር ይችላሉ።\n\n<b>መጋበዣ ሊንክ፦</b> {share_link}"
        else:
            text = f"<b>Ethio Date Converter Bot</b>\n\nInvite your friends to use this bot! You can use it to convert between Gregorian and Ethiopian dates easily.\n\n<b>Referral Link:</b> {share_link}"

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

async def ranks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to view the top referrers leaderboard."""
    try:
        await send_ranks_page(update, context, page=0)
    except Exception as e:
        await send_error(update, context, e, "ranks_command")

async def ranks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles pagination for the leaderboard."""
    try:
        query = update.callback_query
        data = query.data # format: r:{page}
        page = int(data.split(":")[1])
        await send_ranks_page(update, context, page=page)
        await query.answer()
    except Exception as e:
        await send_error(update, context, e, "ranks_callback")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to send a message to all users and group chats."""
    try:
        uid = update.effective_user.id
        if not is_admin_db(uid) and uid not in ADMIN_IDS:
            return

        if not context.args:
            await update.message.reply_text("Usage: /broadcast <message>")
            return

        broadcast_msg = " ".join(context.args)
        user_ids = get_all_user_ids()
        group_ids = get_all_group_ids()
        
        all_targets = user_ids + group_ids
        total = len(all_targets)
        
        status_msg = await update.message.reply_text(
            f"🚀 Starting broadcast to {total} targets...\n"
            f"(👤 Users: {len(user_ids)}, 👥 Groups: {len(group_ids)})"
        )
        
        success = 0
        failed = 0
        blocked = 0
        
        # Combine lists and start broadcasting
        for i, target_id in enumerate(all_targets):
            if is_blocked_db(target_id):
                blocked += 1
                continue
            try:
                await context.bot.send_message(chat_id=target_id, text=broadcast_msg, parse_mode="HTML")
                success += 1
            except Exception as e:
                err_str = str(e).lower()
                if "bot was blocked by the user" in err_str or "user is deactivated" in err_str:
                    blocked += 1
                else:
                    failed += 1
            
            # Rate limiting: ~20 messages per second (avg)
            if i % 20 == 0 and i > 0:
                await asyncio.sleep(1)
                try:
                    await status_msg.edit_text(
                        f"⏳ Broadcasting... {i}/{total}\n"
                        f"✅ Success: {success}\n"
                        f"❌ Failed: {failed+blocked}"
                    )
                except Exception:
                    pass

        report = (
            f"📢 <b>Broadcast Complete</b>\n\n"
            f"👥 Total Targets: {total}\n"
            f"👤 Individual Users: {len(user_ids)}\n"
            f"🏘 Group Chats: {len(group_ids)}\n\n"
            f"✅ Successfully Sent: {success}\n"
            f"🚫 Blocked/Kicked: {blocked}\n"
            f"❌ Other Failures: {failed}"
        )
        await update.message.reply_text(report, parse_mode="HTML")
    except Exception as e:
        await send_error(update, context, e, "broadcast_command")

async def process_e2g(update: Update, context: ContextTypes.DEFAULT_TYPE, d: int, m: int, y: int, lang: str):
    gd, gm, gy = eth_to_greg(d, m, y)
    wk_day = datetime(gy, gm, gd).weekday()
    msg = f"🇺🇸 {gd:02} - {gm:02} - {gy} || {EN_DAYS[wk_day]}, {EN_MONTHS[int(gm)-1]} \n"
    msg += f"🇪🇹 {d} - {m} - {y} || {AM_DAYS[wk_day]} - {AM_MONTHS[int(m)-1]} - {d} "
    await update.message.reply_text(msg, reply_markup=get_menu(update.effective_user.id, lang))
    context.user_data.pop("mode", None)

async def process_age_calc(update: Update, context: ContextTypes.DEFAULT_TYPE, d: int, m: int, y: int, lang: str, mode: str):
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
  #menu commands

async def lang(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [["🇺🇸 English", "🇪🇹 አማርኛ"]]

    await update.message.reply_text(
        "Choose language / ቋንቋ ይምረጡ",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    
async def contact_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the inline 'Contact Admin' button click - prompts user to type their message."""
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
            
        await update.message.reply_text(confirm, reply_markup=get_menu(uid, lang))
        
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
    
async def send_msg_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin_db(uid) and uid not in ADMIN_IDS:
        return

    lang = get_lang(uid)
    args = context.args
    
    # Usage: /send_msg <ID or username> <message>
    if not args:
        msg = "✍️ Please provide User ID or @username.\n\nUsage: <code>/send_msg 12345 Hello there!</code>" if lang == "en" else "✍️ እባክዎ የተጠቃሚውን መለያ (ID) ወይም @username ያስገቡ።\n\nአጠቃቀም፦ <code>/send_msg 12345 ሰላም!</code>"
        await update.message.reply_text(msg, parse_mode="HTML")
        return

    target_query = args[0]
    
    # Try finding user first, then group (group IDs are negative numbers)
    user_data = None
    target_uid = None
    target_name = None
    is_group_target = False
    
    if target_query.lstrip('-').isdigit():
        target_id = int(target_query)
        user_data = get_user_by_id(target_id)
        if not user_data:
            # Check if it's a group ID, trying both the raw target_id and negative version
            potential_group_ids = [target_id]
            if target_id > 0:
                potential_group_ids.append(-target_id)
                # Some groups are -100XXXX...
                if not str(target_id).startswith("100"):
                    potential_group_ids.append(int(f"-100{target_id}"))
                    
            from app.db import get_all_groups
            groups = get_all_groups(limit=1000, offset=0)
            
            for pid in potential_group_ids:
                matched = [(g[0], g[1]) for g in groups if g[0] == pid]
                if matched:
                    target_uid, target_name = matched[0]
                    is_group_target = True
                    break

    else:
        user_data = get_user_by_username(target_query)
        
    if user_data:
        target_uid = user_data[0]
        target_name = user_data[1] or "Unknown"
        
    if target_uid is None:
        msg = f"❌ User/Group <code>{target_query}</code> not found in database." if lang == "en" else f"❌ ተጠቃሚ/ግሩፕ <code>{target_query}</code> በዳታቤዙ ውስጥ አልተገኘም።"
        await update.message.reply_text(msg, parse_mode="HTML")
        return

    if len(args) > 1:
        # Direct send mode
        msg_text = " ".join(args[1:])
        await perform_admin_dm(update, context, target_uid, target_name, msg_text, lang)
    else:
        # Conversational mode
        context.user_data["mode"] = "admin_dm_send"
        context.user_data["target_uid"] = target_uid
        context.user_data["target_name"] = target_name
        
        msg = f"✍️ <b>Sending to:</b> {target_name} [<code>{target_uid}</code>]\n\nPlease type your message below:" if lang=="en" else f"✍️ <b>ለመላክ የተመረጠው፦</b> {target_name} [<code>{target_uid}</code>]\n\nእባክዎን መልዕክትዎን ከታች ይጻፉ፦"
        await update.message.reply_text(msg, parse_mode="HTML")

async def handle_admin_dm_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    target_uid = context.user_data.get("target_uid")
    target_name = context.user_data.get("target_name")
    msg_text = update.message.text

    await perform_admin_dm(update, context, target_uid, target_name, msg_text, lang)

async def perform_admin_dm(update, context, target_uid, target_name, msg_text, lang):
    admin_info = "📨 <b>Message from Admin</b>\n\n"
    final_msg = f"{admin_info}{msg_text}"

    try:
        await context.bot.send_message(
            chat_id=target_uid,
            text=final_msg,
            parse_mode="HTML"
        )
        
        confirm = f"✅ Message sent to {target_name} [<code>{target_uid}</code>]" if lang == "en" else f"✅ መልዕክቱ ለ {target_name} [<code>{target_uid}</code>] ተልኳል።"
        await update.message.reply_text(confirm, parse_mode="HTML")
        
        # Clear data
        context.user_data.pop("mode", None)
        context.user_data.pop("target_uid", None)
        context.user_data.pop("target_name", None)

    except Exception as e:
        await send_error(update, context, e, "perform_admin_dm")
    


    # ERROR_MESSAGE

async def send_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error, func_name, user_msg=None):
    print(f"🛑 ERROR in {func_name}: {error}")
    
    # Get user info if available
    user_info = None
    if update and update.effective_user:
        u = update.effective_user
        user_info = f"{u.full_name} (@{u.username}) [<code>{u.id}</code>]"
    
    report = format_error_report(error, func_name, user_info=user_info)
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
        text = "❌ ያልታወቀ ትዕዛዝ። እባክዎ ከታች ያለውን ማውጫ ይጠቀሙ ወይም ለተጨማሪ መረጃ /help ይጫኑ።"
    else:
        text = "❌ Unknown command. Please use the menu below or type /help for help."
        
    await update.message.reply_text(text, reply_markup=get_menu(update.effective_user.id, lang))

async def health_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to show the secret webhook URL for Cron-job.org."""
    try:
        uid = update.effective_user.id
        if not is_admin_db(uid) and uid not in ADMIN_IDS:
            return

        webhook_url = os.getenv("WEBHOOK_URL")
        if not webhook_url:
            await update.message.reply_text("❌ <b>WEBHOOK_URL</b> is not set in environment variables.")
            return

        secret_link = f"{webhook_url}/{BOT_TOKEN}"
        
        msg = (
            "🟢 <b>Cron-job Success Fix</b>\n\n"
            "Use this secret link in Cron-job.org to get a <b>200 OK (Success)</b> response.\n\n"
            f"🔗 <code>{secret_link}</code>\n\n"
            "⚠️ <b>Note:</b> This link contains your bot token. Keep it private!"
        )
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        await send_error(update, context, e, "health_url")
