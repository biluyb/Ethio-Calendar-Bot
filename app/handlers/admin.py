import html
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .common import send_error, track_activity, get_lang, track_group
from app.db import (
    is_admin_db, get_user_count, search_users, get_all_users, get_user_details,
    is_blocked_db, block_entity_db, unblock_entity_db, get_all_group_ids,
    get_group_count, search_groups, get_all_groups, add_admin_db, remove_admin_db,
    get_admins_db, get_all_user_ids, get_user_by_id, get_user_by_username
)
from app.config import ADMIN_IDS

async def send_users_page(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str = None, page: int = 0, sort_by: str = "last_active_at", order: str = "DESC"):
    """Displays a list of users with pagination and search functionality."""
    try:
        per_page = 10
        
        # Calculate totals
        filter_blocked = (sort_by == "blocked")
        total_count = get_user_count(query or None, filter_blocked=filter_blocked)
        
        if total_count == 0:
            msg = f"❌ <b>No users found</b>"
            if query: msg += f" matching '<code>{query}</code>'"
            if update.message: await update.message.reply_text(msg, parse_mode="HTML")
            else: await update.callback_query.edit_message_text(msg, parse_mode="HTML")
            return

        total_pages = (total_count + per_page - 1) // per_page
        page = max(0, min(page, total_pages - 1))
        offset = page * per_page
        
        # Fetch users
        if query:
            users = search_users(query, sort_by=sort_by, order=order, limit=per_page, offset=offset)
        else:
            users = get_all_users(sort_by=sort_by, order=order, limit=per_page, offset=offset)

        # Build Message
        msg = f"👥 <b>User Management</b> (Total: {total_count})\n"
        if query: msg += f"🔍 Search: <code>{query}</code>\n"
        msg += f"📄 Page: {page + 1}/{total_pages}\n"
        msg += f"━━━━━━━━━━━━━━━━━\n\n"
        
        keyboard = []
        for user in users:
            uid, uname, fname, u_lang, joined, last_act, last_cmd, actions, ref_by, is_blocked, ref_count = user
            
            # Identify name
            display_name = fname or uname or f"User {uid}"
            status_ico = "🚫" if is_blocked else "👤"
            
            msg += f"{status_ico} <b>{display_name}</b> (@{uname})\n"
            msg += f"└── ID: <code>{uid}</code> | {actions} acts\n"
            
            # Specific button for this user
            keyboard.append([InlineKeyboardButton(f"👤 {display_name}", callback_data=f"ud:{uid}:{page}:{sort_by}:{query[:20] if query else ''}")])

        # Navigation Buttons
        nav_btns = []
        if page > 0:
            nav_btns.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"u:{page-1}:{sort_by}:{order}:{query[:20] if query else ''}"))
        if page < total_pages - 1:
            nav_btns.append(InlineKeyboardButton("Next ➡️", callback_data=f"u:{page+1}:{sort_by}:{order}:{query[:20] if query else ''}"))
        if nav_btns:
            keyboard.append(nav_btns)

        # Sorting Options
        sort_label = "Active" if sort_by == "last_active_at" else "Newest" if sort_by == "joined_at" else "Invites" if sort_by == "referrals" else "Blocked"
        keyboard.append([
            InlineKeyboardButton("Activity", callback_data=f"u:0:last_active_at:DESC:{query[:20] if query else ''}"),
            InlineKeyboardButton("Newest", callback_data=f"u:0:joined_at:DESC:{query[:20] if query else ''}"),
            InlineKeyboardButton("Invites", callback_data=f"u:0:referrals:DESC:{query[:20] if query else ''}")
        ])

        if update.message:
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            
    except Exception as e:
        await send_error(update, context, e, "send_users_page")

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to list users."""
    if not is_admin_db(update.effective_user.id): return
    query = " ".join(context.args) if context.args else None
    await send_users_page(update, context, query=query, page=0)

async def users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all callbacks for user management."""
    track_activity(update)
    query = update.callback_query
    data = query.data
    uid = update.effective_user.id
    
    if not is_admin_db(uid):
        await query.answer("Unauthorized access.", show_alert=True)
        return

    # User Detail View
    if data.startswith("ud:"):
        parts = data.split(":")
        target_uid = int(parts[1])
        p_back, s_back, q_back = int(parts[2]), parts[3], parts[4]
        await send_user_detail_view(update, context, target_uid, p_back, s_back, "DESC", q_back)
        
    # Block/Unblock Toggle
    elif data.startswith("toggle_block_user:"):
        parts = data.split(":")
        target_uid = int(parts[1])
        p_back, s_back, o_back, q_back = int(parts[2]), parts[3], parts[4], parts[5]
        
        if is_blocked_db(target_uid):
            unblock_entity_db(target_uid)
            await query.answer(f"User {target_uid} unblocked.")
        else:
            block_entity_db(target_uid)
            await query.answer(f"User {target_uid} blocked.")
            
        await send_user_detail_view(update, context, target_uid, p_back, s_back, o_back, q_back)

    # Navigation / Paging
    elif data.startswith("u:"):
        parts = data.split(":")
        page, sort_by, order, search_q = int(parts[1]), parts[2], parts[3], parts[4]
        await send_users_page(update, context, query=search_q, page=page, sort_by=sort_by, order=order)

    await query.answer()

async def send_user_detail_view(update, context, target_uid, p_back, s_back, o_back, q_back):
    """Detailed view for a specific user."""
    try:
        u = get_user_details(target_uid)
        if not u:
            await update.callback_query.message.edit_text("❌ User not found in database.")
            return

        uid, uname, fname, u_lang, joined, last_act, last_cmd, actions, ref_by, is_blocked, ref_count = u
        
        status_ico = "🚫 Blocked" if is_blocked else "✅ Active"
        j_date = joined.strftime("%Y-%m-%d") if hasattr(joined, 'strftime') else joined
        l_date = last_act.strftime("%Y-%m-%d %H:%M") if hasattr(last_act, 'strftime') else last_act
        
        msg = (
            f"👤 <b>User Profile</b>\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"🏷 <b>Name:</b> {html.escape(fname or 'N/A')}\n"
            f"🔗 <b>Username:</b> @{uname}\n"
            f"🆔 <b>User ID:</b> <code>{uid}</code>\n"
            f"🌍 <b>Language:</b> {u_lang.upper()}\n"
            f"🛡 <b>Status:</b> {status_ico}\n\n"
            f"📅 <b>Joined:</b> {j_date}\n"
            f"⏱ <b>Last Active:</b> {l_date}\n"
            f"📝 <b>Last Cmd:</b> <code>{html.escape(last_cmd or 'N/A')}</code>\n"
            f"🖱 <b>Total Actions:</b> {actions}\n"
            f"👥 <b>Total Invited:</b> {ref_count}\n"
            f"🤝 <b>Referred By:</b> <code>{ref_by or 'None'}</code>"
        )

        keyboard = [
            [
                InlineKeyboardButton("📩 Send Message", callback_data=f"send_msg_init:{uid}"),
                InlineKeyboardButton("✅ Unblock" if is_blocked else "🚫 Block", 
                                     callback_data=f"toggle_block_user:{uid}:{p_back}:{s_back}:{o_back}:{q_back}")
            ],
            [InlineKeyboardButton("⬅️ Back to List", callback_data=f"u:{p_back}:{s_back}:{o_back}:{q_back}")]
        ]

        await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await send_error(update, context, e, "send_user_detail_view")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a message to all users and groups in the database."""
    try:
        uid = update.effective_user.id
        if not is_admin_db(uid) and uid not in ADMIN_IDS:
            return

        cmd_text = update.message.text
        parts = cmd_text.split(maxsplit=1)

        if len(parts) < 2:
            await update.message.reply_text("Usage: /broadcast <message>\n\nOr just type your message with the command.")
            return

        broadcast_msg = parts[1]
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

async def send_msg_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to initiate sending a direct message to a user or group."""
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
                    
            groups = get_all_groups(limit=1000, offset=0)
            
            for pid in potential_group_ids:
                matched = [(g[0], g[1]) for g in groups if g[0] == pid]
                if matched:
                    target_uid, target_name = matched[0]
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
    """Handles the text input for administrative direct messages."""
    uid = update.effective_user.id
    lang = get_lang(uid)
    target_uid = context.user_data.get("target_uid")
    target_name = context.user_data.get("target_name")
    msg_text = update.message.text

    await perform_admin_dm(update, context, target_uid, target_name, msg_text, lang)

async def perform_admin_dm(update: Update, context: ContextTypes.DEFAULT_TYPE, target_uid: int, target_name: str, msg_text: str, lang: str):
    """Executes the actual sending of an administrative direct message."""
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

async def groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to list groups the bot is in."""
    if not is_admin_db(update.effective_user.id): return
    query = " ".join(context.args) if context.args else None
    await send_groups_page(update, context, 0, query)

async def groups_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles pagination for the groups list."""
    track_activity(update)
    query = update.callback_query
    data = query.data # g:{page}:{query}
    parts = data.split(":")
    page = int(parts[1])
    search_q = parts[2] if len(parts) > 2 else None
    await send_groups_page(update, context, page, search_q)
    await query.answer()

async def send_groups_page(update, context, page, query):
    """Internal function to display the paginated groups list."""
    try:
        per_page = 10
        count = get_group_count(query)
        groups = search_groups(query, limit=per_page, offset=page*per_page) if query else get_all_groups(limit=per_page, offset=page*per_page)
        
        total_pages = (count + per_page - 1) // per_page
        
        msg = f"🏘️ <b>Group Chats</b> (Total: {count})\n"
        if query: msg += f"🔍 Search: <code>{query}</code>\n"
        msg += f"📄 Page: {page + 1}/{total_pages}\n"
        msg += "━━━━━━━━━━━━━━━━━\n\n"
        
        for g in groups:
            gid, title, joined, is_blocked = g
            status = "🚫 " if is_blocked else ""
            msg += f"• {status}<b>{html.escape(title or 'Unnamed Group')}</b>\n   ID: <code>{gid}</code>\n"
        
        kb = []
        nav = []
        q_suffix = f":{query}" if query else ""
        if page > 0: nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"g:{page-1}{q_suffix}"))
        if page < total_pages - 1: nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"g:{page+1}{q_suffix}"))
        if nav: kb.append(nav)
        
        if update.message:
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb) if kb else None)
        else:
            await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb) if kb else None)
    except Exception as e:
        await send_error(update, context, e, "send_groups_page")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super-Admin command to add a new admin."""
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        if not context.args:
            await update.message.reply_text("Usage: /addadmin <UserID>")
            return
        target_id = int(context.args[0])
        add_admin_db(target_id)
        await update.message.reply_text(f"✅ User <code>{target_id}</code> added to admins.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error adding admin: {e}")

async def del_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Super-Admin command to remove an admin."""
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        if not context.args:
            await update.message.reply_text("Usage: /deladmin <UserID>")
            return
        target_id = int(context.args[0])
        remove_admin_db(target_id)
        await update.message.reply_text(f"✅ User <code>{target_id}</code> removed from admins.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error removing admin: {e}")

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all current admins."""
    if not is_admin_db(update.effective_user.id) and update.effective_user.id not in ADMIN_IDS:
        return
    try:
        admins = set(get_admins_db()) | set(ADMIN_IDS)
        msg = "🛡️ <b>Bot Administrators</b>\n\n"
        for i, aid in enumerate(admins, 1):
            is_super = " (Super)" if aid in ADMIN_IDS else ""
            msg += f"{i}. <code>{aid}</code>{is_super}\n"
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        await send_error(update, context, e, "list_admins")

async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Blocks a user or group across the entire bot."""
    if not is_admin_db(update.effective_user.id): return
    try:
        if not context.args:
            await update.message.reply_text("Usage: /block <targetID>")
            return
        tid = int(context.args[0])
        block_entity_db(tid)
        await update.message.reply_text(f"✅ ID <code>{tid}</code> has been blocked.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error blocking: {e}")

async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unblocks a previously blocked user or group."""
    if not is_admin_db(update.effective_user.id): return
    try:
        if not context.args:
            await update.message.reply_text("Usage: /unblock <targetID>")
            return
        tid = int(context.args[0])
        unblock_entity_db(tid)
        await update.message.reply_text(f"✅ ID <code>{tid}</code> has been unblocked.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error unblocking: {e}")

async def leavegroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forces the bot to leave a specific group."""
    if not is_admin_db(update.effective_user.id): return
    try:
        if not context.args:
            await update.message.reply_text("Usage: /leavegroup <groupID>")
            return
        gid = int(context.args[0])
        await context.bot.leave_chat(chat_id=gid)
        await update.message.reply_text(f"✅ Successfully left group <code>{gid}</code>", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to leave group: {e}")
