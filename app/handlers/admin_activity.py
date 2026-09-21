"""
Admin Activity Tracking Handler
Displays admin activity logs with admin directory selection, pagination, and detailed human-readable activity descriptions.
"""
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.db import get_lang, is_admin_db, get_admins_db, get_user_by_id
from app.db.activity_db import get_admin_activity, get_admin_activity_count, get_admin_activity_summary
from app.config import ADMIN_IDS
from .common import send_error, track_activity


def log_admin(uid: int, action: str, detail: str = None, target_id: int = None):
    """Convenience wrapper: log an admin action silently."""
    try:
        from app.db.activity_db import log_admin_action
        log_admin_action(uid, action, detail, target_id)
    except Exception as e:
        print(f"Activity log warning: {e}")


def get_user_badge(uid: int) -> str:
    """Formats a user/admin ID into a human-readable name & tag."""
    if not uid:
        return ""
    try:
        u = get_user_by_id(uid)
        if u:
            full_name = u[2]
            username = u[1]
            if full_name and username:
                return f"<b>{html.escape(full_name)}</b> (@{html.escape(username)}) [<code>{uid}</code>]"
            elif full_name:
                return f"<b>{html.escape(full_name)}</b> [<code>{uid}</code>]"
            elif username:
                return f"<b>@{html.escape(username)}</b> [<code>{uid}</code>]"
    except Exception:
        pass
    return f"<code>{uid}</code>"


def get_action_icon(action: str) -> str:
    """Returns a visual emoji icon for common admin actions."""
    a = action.lower()
    if "broadcast" in a:
        return "📢"
    elif "send_msg" in a or "dm" in a:
        return "✉️"
    elif "reply" in a:
        return "💬"
    elif "addadmin" in a:
        return "➕"
    elif "deladmin" in a:
        return "➖"
    elif "block" in a and "unblock" not in a:
        return "⛔"
    elif "unblock" in a:
        return "✅"
    elif "leavegroup" in a:
        return "🚪"
    elif "api" in a or "key" in a:
        return "🔐"
    return "⚡"


async def admin_activity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /admin_activity — Displays the Admin Directory view by default.
    """
    uid = update.effective_user.id
    if not is_admin_db(uid) and uid not in ADMIN_IDS:
        return

    track_activity(update, "/admin_activity")
    await send_admin_directory_page(update, context, page=0)


async def admin_activity_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback router for activity log buttons:
    - act:dir:{page} -> Admin Directory
    - act:log:{admin_id}:{page} -> Specific Admin Log or 'all'
    - legacy fallback act:{page}:{admin_id}
    """
    try:
        query = update.callback_query
        uid = update.effective_user.id

        if not is_admin_db(uid) and uid not in ADMIN_IDS:
            await query.answer("Unauthorized", show_alert=True)
            return

        track_activity(update)
        data = query.data

        if data in ["act_summary", "act:dir", "act:dir:0"]:
            await send_admin_directory_page(update, context, page=0)
            await query.answer()
            return

        if data.startswith("act:dir:"):
            page = int(data.split(":")[2])
            await send_admin_directory_page(update, context, page=page)
            await query.answer()
            return

        if data.startswith("act:log:"):
            parts = data.split(":")
            target_admin = parts[2]
            page = int(parts[3])
            await send_activity_log_page(update, context, admin_id_param=target_admin, page=page)
            await query.answer()
            return

        # Legacy fallback parsing: act:{page}:{filter_admin}
        parts = data.split(":")
        if len(parts) >= 2 and parts[1].isdigit():
            page = int(parts[1])
            filter_admin = parts[2] if len(parts) > 2 and parts[2] not in ["", "0"] else "all"
            await send_activity_log_page(update, context, admin_id_param=filter_admin, page=page)
            await query.answer()
            return

        await send_admin_directory_page(update, context, page=0)
        await query.answer()

    except Exception as e:
        await send_error(update, context, e, "admin_activity_callback")


async def send_admin_directory_page(update, context, page: int = 0):
    """
    Renders the Admin Directory view — listing all administrators with action stats and select buttons.
    """
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)

        # Build complete list of all known admins
        summary_rows = get_admin_activity_summary()
        summary_dict = {row[0]: (row[1], row[2]) for row in summary_rows}

        all_admin_ids = set(get_admins_db()) | set(ADMIN_IDS) | set(summary_dict.keys())

        admin_list = []
        for aid in all_admin_ids:
            total_actions, last_act = summary_dict.get(aid, (0, "N/A"))
            admin_list.append({
                "id": aid,
                "total_actions": total_actions,
                "last_act": last_act
            })

        # Sort admins by total actions & last active date (newest first)
        admin_list.sort(key=lambda x: (x["total_actions"], str(x["last_act"])), reverse=True)

        per_page = 5
        total_admins = len(admin_list)
        total_pages = max(1, (total_admins + per_page - 1) // per_page)
        page = min(page, total_pages - 1)

        start_idx = page * per_page
        page_admins = admin_list[start_idx:start_idx + per_page]

        if lang == "am":
            title = "👥 <b>የአድሚን ምዝግብ ማስታወሻ — የአድሚኖች ዝርዝር</b>"
            subtitle = "<i>እባክዎን እንቅስቃሴውን ለማየት አድሚን ይምረጡ፦</i>\n"
        else:
            title = "👥 <b>Admin Activity Log — Admin Directory</b>"
            subtitle = "<i>Select an administrator to view detailed activity history:</i>\n"

        msg = f"{title}\n{subtitle}"
        msg += f"📄 Page: <b>{page+1}/{total_pages}</b>  (Total Admins: {total_admins})\n"
        msg += "━━━━━━━━━━━━━━━━━\n\n"

        for i, ainfo in enumerate(page_admins, start=start_idx + 1):
            aid = ainfo["id"]
            tot = ainfo["total_actions"]
            last_t = str(ainfo["last_act"])[:16]
            is_super = " ⭐️" if aid in ADMIN_IDS else ""
            badge = get_user_badge(aid)
            msg += f"{i}. 👤 {badge}{is_super}\n"
            msg += f"    📊 <b>{tot}</b> actions | 🕐 Last: {last_t}\n\n"

        keyboard = []

        # Per-admin selection buttons
        for ainfo in page_admins:
            aid = ainfo["id"]
            tot = ainfo["total_actions"]
            u = get_user_by_id(aid)
            label_name = (u[2] if u and u[2] else (f"@{u[1]}" if u and u[1] else f"ID {aid}"))
            btn_text = f"👤 {label_name[:16]} ({tot})"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"act:log:{aid}:0")])

        # Master Log button
        all_text = "🌐 ሁሉንም አድሚኖች ይመልከቱ (All Log)" if lang == "am" else "🌐 Master Log (All Admins Combined)"
        keyboard.append([InlineKeyboardButton(all_text, callback_data="act:log:all:0")])

        # Directory pagination row
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"act:dir:{page-1}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"act:dir:{page+1}"))
        if nav:
            keyboard.append(nav)

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.message:
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)

    except Exception as e:
        await send_error(update, context, e, "send_admin_directory_page")


async def send_activity_log_page(update, context, admin_id_param="all", page: int = 0):
    """
    Renders the detailed activity log list for a specific admin or all admins.
    """
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)

        is_all = str(admin_id_param) in ["all", "0", "None"]
        filter_admin = None if is_all else int(admin_id_param)

        per_page = 10
        total = get_admin_activity_count(filter_admin)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = min(page, total_pages - 1)
        offset = page * per_page

        rows = get_admin_activity(filter_admin, limit=per_page, offset=offset)

        if is_all:
            header_target = "Master Log (All Admins)" if lang == "en" else "የሁሉም አድሚኖች እንቅስቃሴ"
        else:
            header_target = get_user_badge(filter_admin)

        if lang == "am":
            title = f"📋 <b>የአድሚን እንቅስቃሴ፦</b> {header_target}"
        else:
            title = f"📋 <b>Admin Activity Log:</b> {header_target}"

        msg = f"{title}\n"
        msg += f"📄 Page: <b>{page+1}/{total_pages}</b>  (Total: {total} logged actions)\n"
        msg += "━━━━━━━━━━━━━━━━━\n\n"

        if not rows:
            msg += "<i>ምንም እንቅስቃሴ አልተመዘገበም።</i>" if lang == "am" else "<i>No recorded activity found for this selection.</i>"
        else:
            for row in rows:
                row_id, admin_id, action, detail, target_id, performed_at = row
                time_str = str(performed_at)[:16]
                icon = get_action_icon(action)

                clean_action = html.escape(action[:60])
                clean_detail = html.escape((detail or "")[:200])

                msg += f"{icon} <b>{clean_action}</b>\n"

                if is_all:
                    admin_badge = get_user_badge(admin_id)
                    msg += f"   👤 <b>Admin:</b> {admin_badge}\n"

                if target_id:
                    target_badge = get_user_badge(target_id)
                    msg += f"   🎯 <b>Target:</b> {target_badge}\n"

                msg += f"   🕐 <b>Time:</b> <code>{time_str}</code>\n"

                if clean_detail:
                    msg += f"   📝 <i>{clean_detail}</i>\n"

                msg += "\n"

        keyboard = []
        nav = []
        target_str = str(admin_id_param)

        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"act:log:{target_str}:{page-1}"))
        nav.append(InlineKeyboardButton(f"🔄 {page+1}/{total_pages}", callback_data=f"act:log:{target_str}:{page}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"act:log:{target_str}:{page+1}"))
        if nav:
            keyboard.append(nav)

        back_txt = "👥 የአድሚኖች ዝርዝር (Admins List)" if lang == "am" else "👥 Admins Directory"
        keyboard.append([InlineKeyboardButton(back_txt, callback_data="act:dir:0")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.message:
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)

    except Exception as e:
        await send_error(update, context, e, "send_activity_log_page")
