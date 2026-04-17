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

async def send_users_page(update, context, query, page, sort_by="last_active_at", order="DESC"):
    try:
        per = 10
        count = get_user_count(query or None, filter_blocked=(sort_by=="blocked"))
        if count == 0:
            msg = "❌ No users found."
            if update.message: await update.message.reply_text(msg)
            else: await update.callback_query.edit_message_text(msg)
            return
        tp = (count + per - 1) // per
        page = max(0, min(page, tp - 1))
        users = search_users(query, sort_by=sort_by, order=order, limit=per, offset=page*per) if query else get_all_users(sort_by=sort_by, order=order, limit=per, offset=page*per)
        
        msg = f"👥 <b>Total:</b> {count}\n📄 Page {page+1}/{tp}\n\n"
        kb = []
        for u in users:
            uid, uname, fname = u[0], u[1], u[2]
            msg += f"• {'🚫 ' if u[9] else ''}<b>{uname}</b> (<code>{uid}</code>)\n"
            kb.append([InlineKeyboardButton(f"👤 {fname or uname}", callback_data=f"ud:{uid}:{page}:{sort_by}:{query[:20] if query else ''}")])
        
        nav = []
        if page > 0: nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"u:{page-1}:{sort_by}:{order}:{query[:20] if query else ''}"))
        if page < tp - 1: nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"u:{page+1}:{sort_by}:{order}:{query[:20] if query else ''}"))
        if nav: kb.append(nav)
        
        # Sort Buttons
        kb.append([InlineKeyboardButton("Activity", callback_data=f"u:0:last_active_at:DESC:{query[:20] if query else ''}"),
                   InlineKeyboardButton("Newest", callback_data=f"u:0:joined_at:DESC:{query[:20] if query else ''}")])
        
        if update.message: await update.message.reply_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
        else: await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e: await send_error(update, context, e, "users_page")

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_db(update.effective_user.id): return
    await send_users_page(update, context, " ".join(context.args), 0)

async def users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin_db(update.effective_user.id): return
    data = query.data
    if data.startswith("ud:"):
        p = data.split(":")
        await send_user_detail_view(update, context, int(p[1]), int(p[2]), p[3], "DESC", p[5] if len(p)>5 else "")
    elif data.startswith("toggle_block_user:"):
        p = data.split(":")
        tid = int(p[1])
        if is_blocked_db(tid): unblock_entity_db(tid)
        else: block_entity_db(tid)
        await send_user_detail_view(update, context, tid, int(p[2]), p[3], p[4], p[5] if len(p)>5 else "")
    elif data.startswith("u:"):
        p = data.split(":")
        await send_users_page(update, context, p[4] if len(p)>4 else "", int(p[1]), p[2], p[3] if len(p)>3 else "DESC")
    await query.answer()

async def send_user_detail_view(update, context, target_uid, p_back, s_back, o_back, q_back):
    u = get_user_details(target_uid)
    if not u: return
    msg = f"👤 <b>{u[2] or u[1]}</b>\nID: <code>{u[0]}</code>\nBlocked: {'Yes' if u[9] else 'No'}"
    kb = [[InlineKeyboardButton("📩 Send Message", callback_data=f"send_msg_init:{u[0]}"),
           InlineKeyboardButton("✅ Unblock" if u[9] else "🚫 Block", callback_data=f"toggle_block_user:{u[0]}:{p_back}:{s_back}:{o_back}:{q_back}")],
          [InlineKeyboardButton("⬅️ Back", callback_data=f"u:{p_back}:{s_back}:{o_back}:{q_back}")]]
    await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin_db(uid) and uid not in ADMIN_IDS: return
    parts = update.message.text.split(maxsplit=1)
    if len(parts) < 2: return await update.message.reply_text("Usage: /broadcast <message>")
    
    msg = parts[1]
    targets = get_all_user_ids() + get_all_group_ids()
    status = await update.message.reply_text(f"🚀 Broadcasting to {len(targets)}...")
    
    success, failed = 0, 0
    for i, tid in enumerate(targets):
        try:
            await context.bot.send_message(chat_id=tid, text=msg, parse_mode="HTML")
            success += 1
        except: failed += 1
        if i % 20 == 0: await asyncio.sleep(1)
    await update.message.reply_text(f"✅ Sent: {success}, ❌ Failed: {failed}")

async def send_msg_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_db(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("Usage: /send_msg <id> <msg>")
    
    target = context.args[0]
    u = get_user_by_id(int(target)) if target.lstrip('-').isdigit() else get_user_by_username(target)
    if not u: return await update.message.reply_text("❌ Not found")
    
    if len(context.args) > 1:
        await context.bot.send_message(chat_id=u[0], text=f"📨 <b>Admin:</b> {' '.join(context.args[1:])}", parse_mode="HTML")
        await update.message.reply_text("✅ Sent")
    else:
        context.user_data.update({"mode": "admin_dm_send", "target_uid": u[0], "target_name": u[1] or u[2]})
        await update.message.reply_text(f"✍️ Sending to {u[1]}. Type message:")

async def groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_db(update.effective_user.id): return
    await send_groups_page(update, context, 0, " ".join(context.args) if context.args else None)

async def groups_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = update.callback_query.data.split(":")
    await send_groups_page(update, context, int(p[1]), p[2] if len(p)>2 else None)
    await update.callback_query.answer()

async def send_groups_page(update, context, page, query):
    count = get_group_count(query)
    groups = search_groups(query, limit=10, offset=page*10) if query else get_all_groups(limit=10, offset=page*10)
    msg = f"🏘️ <b>Groups:</b> {count}\n\n"
    for g in groups: msg += f"• {g[1]} (<code>{g[0]}</code>)\n"
    kb = []
    if page > 0: kb.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"g:{page-1}:{query or ''}"))
    if (page+1)*10 < count: kb.append(InlineKeyboardButton("Next ➡️", callback_data=f"g:{page+1}:{query or ''}"))
    await (update.message.reply_text if update.message else update.callback_query.edit_message_text)(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([kb]) if kb else None)

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    if not context.args: return
    add_admin_db(int(context.args[0]))
    await update.message.reply_text("✅ Added")

async def del_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    if not context.args: return
    remove_admin_db(int(context.args[0]))
    await update.message.reply_text("✅ Removed")

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = set(get_admins_db()) | set(ADMIN_IDS)
async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_db(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("Usage: /block <id>")
    tid = int(context.args[0])
    block_entity_db(tid)
    await update.message.reply_text(f"✅ Blocked <code>{tid}</code>", parse_mode="HTML")

async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_db(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("Usage: /unblock <id>")
    tid = int(context.args[0])
    unblock_entity_db(tid)
    await update.message.reply_text(f"✅ Unblocked <code>{tid}</code>", parse_mode="HTML")

async def leavegroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_db(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("Usage: /leavegroup <id>")
    try:
        gid = int(context.args[0])
        await context.bot.leave_chat(chat_id=gid)
        await update.message.reply_text(f"✅ Left group <code>{gid}</code>", parse_mode="HTML")
    except Exception as e: await update.message.reply_text(f"❌ Failed: {e}")
