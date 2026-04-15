"""
Main Entry Point for the Ethiopian Calendar Bot.
Configures the Telegram Application, registers command handlers, 
and manages the production/local lifecycle.
"""

import os
import logging
from telegram import BotCommand
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    filters
)

# Configuration & Submodules
from app.config import BOT_TOKEN, ADMIN_IDS
from app.db import init_db, add_admin_db, get_admins_db
from app.handlers import (
    start, 
    handle, 
    today,
    lang as lang_keyboard, 
    info as help_info, 
    share_command,
    ranks_command,
    help_command,
    unknown_command,
    notify_admin, 
    format_error_report,
    users, 
    users_callback, 
    ranks_callback,
    broadcast_command,
    groups_command,
    groups_callback,
    age_mode_callback, 
    add_admin, 
    del_admin, 
    list_admins, 
    contact_admin_callback,
    admin_reply_callback,
    send_msg_command,
    block_command,
    unblock_command,
    leavegroup_command,
    USER_CMDS,
    refresh_user_commands
)

# Environment Overrides
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

async def global_error_handler(update, context):
    """
    Global catch-all for errors not handled at the command level.
    Logs the error and notifies admins via the standardized reporting system.
    """
    # Standard logging
    logging.error(f"GLOBAL EXCEPTION: {context.error}")
    
    # Broadcast to maintainers
    report = format_error_report(context.error, "GLOBAL_DISPATCHER")
    if report:
        try:
            await notify_admin(context, report)
        except Exception:
            pass # Prevent error loop if notification itself fails

def main():
    """
    Initializes the system and starts the bot.
    Handles DB setup, role synchronization, and handler registration.
    """
    # 1. Database & Role Initialization
    init_db()
    
    # Synchronize primary admins from config to database
    existing_admins = set(get_admins_db())
    for aid in ADMIN_IDS:
        if aid not in existing_admins:
            add_admin_db(aid)

    # 2. Application Setup
    async def post_init(application):
        """Logic to run after the bot starts (e.g., dynamic command registration)."""
        # Set default commands for all users
        await application.bot.set_my_commands(USER_CMDS)

        # Set specialized commands for admins
        all_admins = set(get_admins_db()) | set(ADMIN_IDS)
        for uid in all_admins:
            await refresh_user_commands(application.bot, uid)

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .concurrent_updates(True)
        .connect_timeout(30)
        .read_timeout(30)
        .build()
    )

    # 3. Handlers Registration
    # Command Handlers
    app.add_handler(CommandHandler(["start", "menu"], start))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("lang", lang_keyboard))
    app.add_handler(CommandHandler("info", help_info))
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
    
    # Callback Handlers (Inline Buttons)
    app.add_handler(CallbackQueryHandler(users_callback, pattern="^u:"))
    app.add_handler(CallbackQueryHandler(ranks_callback, pattern="^r:"))
    app.add_handler(CallbackQueryHandler(age_mode_callback, pattern="^age_mode_"))
    app.add_handler(CallbackQueryHandler(groups_callback, pattern="^g:"))
    app.add_handler(CallbackQueryHandler(contact_admin_callback, pattern="^contact_admin_request$"))
    app.add_handler(CallbackQueryHandler(admin_reply_callback, pattern="^admin_reply_"))

    # Content Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    
    # Fallback (must be last)
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Error Management
    app.add_error_handler(global_error_handler)

    # 4. Lifecycle Execution
    print(f"🚀 Bot starting (Environment: {'Production' if WEBHOOK_URL else 'Development'})...")
    
    if WEBHOOK_URL:
        # Production: Webhook Mode
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
    else:
        # Development: Polling Mode
        app.run_polling()

if __name__ == "__main__":
    main()
