from .common import (
    USER_CMDS, ADMIN_CMDS, SUPER_ADMIN_CMDS, track_activity, get_menu,
    notify_admin, format_error_report, send_error
)
from .user import (
    start, today, language as lang, calendar_command, about_command, share_command, 
    ranks_command, ranks_callback, refresh_user_commands, help_command
)
from .api import api_key_command, api_stats_command, api_stats_callback, api_download_guide_handler
from .admin import (
    users, users_callback, groups_command, groups_callback, 
    broadcast_command, send_msg_command, handle_admin_dm_send,
    add_admin, del_admin, list_admins,
    block_command, unblock_command, leavegroup_command,
    admin_broadcast_callback
)
from .callbacks import age_mode_callback, contact_admin_callback
from .main_handler import (
    handle, admin_reply_callback, handle_admin_reply_to_user, 
    unknown_command, chat_member_callback
)
from .extra import health_url
from .calendar_view import calendar_view_command, calendar_view_callback, my_reminders_command, handle_reminder_text_input
from .admin_activity import (
    admin_activity_command, admin_activity_callback, 
    admin_activity_summary_callback
)

import logging
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    filters,
)


async def global_error_handler(update, context):
    """
    Global catch-all for errors not handled at the command level.
    Logs the error and notifies admins via the standardized reporting system.
    """
    logging.error(f"GLOBAL EXCEPTION: {context.error}")

    # Broadcast to maintainers
    report = format_error_report(context.error, "GLOBAL_DISPATCHER")
    if report:
        try:
            await notify_admin(context, report)
        except Exception:
            pass  # Prevent error loop if notification itself fails


def register_handlers(app):
    """Registers every Telegram command, callback, message and state handler.

    Centralizes handler registration so the entrypoint stays a thin lifecycle
    wrapper. Callback handlers are matched by prefix patterns, so the fallback
    command handler must be added last.
    """
    # Command Handlers
    app.add_handler(CommandHandler(["start", "menu"], start))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("lang", lang))
    app.add_handler(CommandHandler(["calendar", "info"], calendar_command))
    app.add_handler(CommandHandler(["view_calendar", "vcal"], calendar_view_command))
    app.add_handler(CommandHandler(["reminders", "my_reminders"], my_reminders_command))
    app.add_handler(CommandHandler("admin_activity", admin_activity_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("api", api_key_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("share", share_command))
    app.add_handler(CommandHandler("ranks", ranks_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CommandHandler("groups", groups_command))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("deladmin", del_admin))
    app.add_handler(CommandHandler("listadmins", list_admins))
    app.add_handler(CommandHandler("send_msg", send_msg_command))
    app.add_handler(CommandHandler("block", block_command))
    app.add_handler(CommandHandler("unblock", unblock_command))
    app.add_handler(CommandHandler("leavegroup", leavegroup_command))
    app.add_handler(CommandHandler("api_stats", api_stats_command))
    app.add_handler(CommandHandler("health_url", health_url))

    # Callback Handlers (Inline Buttons)
    app.add_handler(CallbackQueryHandler(users_callback, pattern="^(u:|ud:|toggle_block_user:|send_msg_init:)"))
    app.add_handler(CallbackQueryHandler(ranks_callback, pattern="^r:"))
    app.add_handler(CallbackQueryHandler(age_mode_callback, pattern="^age_mode_"))
    app.add_handler(CallbackQueryHandler(groups_callback, pattern="^g:"))
    app.add_handler(CallbackQueryHandler(api_stats_callback, pattern="^(api_dash:|api_revoke_prompt|api_regen_prompt|api_reset_prompt|api_broadcast_prompt)"))
    app.add_handler(CallbackQueryHandler(api_download_guide_handler, pattern="^api_download_guide$"))
    app.add_handler(CallbackQueryHandler(contact_admin_callback, pattern="^contact_admin_request$"))
    app.add_handler(CallbackQueryHandler(admin_reply_callback, pattern="^admin_reply_"))
    app.add_handler(CallbackQueryHandler(admin_broadcast_callback, pattern="^bc_report:"))
    # Calendar view & reminder callbacks (EC & GC dual mode)
    app.add_handler(CallbackQueryHandler(calendar_view_callback, pattern="^(cal:|cal_months:|cal_day:|cal_ignore|gcal:|gcal_months:|gcal_day:|rem_add:|rem_del:|my_reminders|show_calendar_info)"))
    # Admin activity callbacks
    app.add_handler(CallbackQueryHandler(admin_activity_callback, pattern="^act:"))
    app.add_handler(CallbackQueryHandler(admin_activity_summary_callback, pattern="^act_summary$"))

    # Content Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    # State Handlers
    app.add_handler(ChatMemberHandler(chat_member_callback, ChatMemberHandler.MY_CHAT_MEMBER))

    # Fallback (must be last)
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Error Management
    app.add_error_handler(global_error_handler)
