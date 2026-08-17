"""
Admin Activity Tracking Handler
Displays the admin activity log with pagination and per-admin filtering.
"""
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.db import get_lang, is_admin_db
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


async def admin_activity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /admin_activity — Shows paginated admin activity log.
    Accessible only to admins.
    """
    uid = update.effective_user.id
    if not is_admin_db(uid) and uid not in ADMIN_IDS:
        return

    lang = get_lang(uid)
    track_activity(update, "/admin_activity")
    log_admin(uid, "/admin_activity", "Viewed activity log")

    await send_activity_page(update, context, page=0, filter_admin=None)


async def admin_activity_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles: act:{page}:{filter_admin_id}
    """
    try:
        query = update.callback_query
        uid = update.effective_user.id

        if not is_admin_db(uid) and uid not in ADMIN_IDS:
            await query.answer("Unauthorized", show_alert=True)
            return

        data = query.data  # act:{page}:{filter}
        parts = data.split(":")
        page = int(parts[1])
        filter_admin = int(parts[2]) if len(parts) > 2 and parts[2] not in ["", "0"] else None

        track_activity(update)
        await send_activity_page(update, context, page=page, filter_admin=filter_admin)
        await query.answer()
    except Exception as e:
        await send_error(update, context, e, "admin_activity_callback")


async def send_activity_page(update, context, page: int = 0, filter_admin: int = None):
    """Renders the activity log page."""
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)

        per_page = 15
        offset = page * per_page
        total = get_admin_activity_count(filter_admin)
        total_pages = max(1, (total + per_page - 1) // per_page)
        rows = get_admin_activity(filter_admin, limit=per_page, offset=offset)

        if lang == "am":
            title = "📋 <b>አድሚን እንቅስቃሴ ምዝግብ ማስታወሻ</b>"
            if filter_admin:
                title += f"\n🔍 <i>ለ Admin ID: <code>{filter_admin}</code></i>"
        else:
            title = "📋 <b>Admin Activity Log</b>"
            if filter_admin:
                title += f"\n🔍 <i>Filter: Admin <code>{filter_admin}</code></i>"

        msg = f"{title}\n"
        msg += f"📄 Page: <b>{page+1}/{total_pages}</b>  (Total: {total})\n"
        msg += "━━━━━━━━━━━━━━━━━\n\n"

        if not rows:
            msg += "<i>No activity recorded yet.</i>" if lang == "en" else "<i>ምንም እንቅስቃሴ አልተመዘገበም።</i>"
        else:
            for row in rows:
                row_id, admin_id, action, detail, target_id, performed_at = row
                time_str = str(performed_at)[:16]
                clean_action = html.escape(action[:60])
                clean_detail = html.escape((detail or "")[:80])
                target_str = f" → <code>{target_id}</code>" if target_id else ""
                msg += (
                    f"⚡ <b>{clean_action}</b>{target_str}\n"
                    f"   👤 <code>{admin_id}</code>  🕐 {time_str}\n"
                )
                if clean_detail:
                    msg += f"   📝 <i>{clean_detail}</i>\n"
                msg += "\n"

        keyboard = []
        nav = []
        filter_str = str(filter_admin) if filter_admin else "0"
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"act:{page-1}:{filter_str}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"act:{page+1}:{filter_str}"))
        if nav:
            keyboard.append(nav)

        # Summary / per-admin filter
        keyboard.append([InlineKeyboardButton("📊 Summary", callback_data="act_summary")])

        if filter_admin:
            keyboard.append([InlineKeyboardButton("🔄 All Admins", callback_data="act:0:0")])

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        if update.message:
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)

    except Exception as e:
        await send_error(update, context, e, "send_activity_page")


async def admin_activity_summary_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows a summary of actions per admin."""
    try:
        query = update.callback_query
        uid = update.effective_user.id

        if not is_admin_db(uid) and uid not in ADMIN_IDS:
            await query.answer("Unauthorized", show_alert=True)
            return

        lang = get_lang(uid)
        rows = get_admin_activity_summary()

        if lang == "am":
            msg = "📊 <b>አድሚን እንቅስቃሴ ማጠቃለያ</b>\n\n"
        else:
            msg = "📊 <b>Admin Activity Summary</b>\n\n"
        msg += "━━━━━━━━━━━━━━━━━\n"

        keyboard = []
        if not rows:
            msg += "<i>No data yet.</i>"
        else:
            for i, (admin_id, total_actions, last_action) in enumerate(rows, 1):
                last_str = str(last_action)[:16]
                msg += f"{i}. 👤 <code>{admin_id}</code> — <b>{total_actions}</b> actions\n    🕐 Last: {last_str}\n\n"
                keyboard.append([
                    InlineKeyboardButton(
                        f"View {admin_id}",
                        callback_data=f"act:0:{admin_id}"
                    )
                ])

        keyboard.append([InlineKeyboardButton("📋 Full Log", callback_data="act:0:0")])
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        await query.answer()
    except Exception as e:
        await send_error(update, context, e, "admin_activity_summary_callback")
