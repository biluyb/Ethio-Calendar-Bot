import os
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from app.config import BOT_TOKEN, ADMIN_IDS
from app.handlers import (
    start, 
    handle, 
    today,
    lang as lang_keyboard, 
    info as help_info, 
    bot_info as dev_info,
    send_users_command,
    share_command,
    ranks_command,
    help_command,
    unknown_command,
    notify_admin, 
    format_error_report,
    users, 
    users_callback, 
    age_mode_callback, 
    add_admin, 
    del_admin, 
    list_admins, 
    contact_admin_callback, 
    admin_reply_callback,
    send_msg_command,
    USER_CMDS,
    refresh_user_commands
)


async def error_handler(update, context):
    print(f"🛑 GLOBAL ERROR: {context.error}")
    
    report = format_error_report(context.error, "GLOBAL_DISPATCHER")
    if report:
        await notify_admin(context, report)

from app.db import init_db, add_admin_db, get_admins_db

# Webhook Config
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_URL = os.getenv("WEBHOOK_URL") # Provided by Render/Koyeb

def main():
    # Initialize Database
    init_db()
    
    # Sync primary admins to DB
    existing_admins = set(get_admins_db())
    for aid in ADMIN_IDS:
        if aid not in existing_admins:
            add_admin_db(aid)

    async def post_init(application):
        # 1. Set default commands for all users
        await application.bot.set_my_commands(USER_CMDS)

        # 2. Set specialized commands for admins and super admins
        admins = set(get_admins_db()) | set(ADMIN_IDS)
        for uid in admins:
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


    # COMMANDS
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("lang", lang_keyboard))
    app.add_handler(CommandHandler("info", help_info))
    app.add_handler(CommandHandler("about", dev_info))
    app.add_handler(CommandHandler("help", help_command))
    
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("deladmin", del_admin))
    app.add_handler(CommandHandler("listadmins", list_admins))
    app.add_handler(CommandHandler("send_msg", send_msg_command))
    
    # CALLBACKS
    app.add_handler(CallbackQueryHandler(users_callback, pattern="^u:"))
    app.add_handler(CallbackQueryHandler(age_mode_callback, pattern="^age_mode_"))
    app.add_handler(CallbackQueryHandler(contact_admin_callback, pattern="^contact_admin_request$"))
    app.add_handler(CallbackQueryHandler(admin_reply_callback, pattern="^admin_reply_"))

    # TEXT HANDLER
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    
    # UNKNOWN COMMAND HANDLER (Must be last)
    app.add_handler(CommandHandler("share", share_command))
    app.add_handler(CommandHandler("ranks", ranks_command))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    app.add_error_handler(error_handler)

    print(f"✅ Bot starting (Mode: {'Webhook' if WEBHOOK_URL else 'Polling'})...")
    
    if WEBHOOK_URL:
        # Webhook Mode (Production)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
    else:
        # Polling Mode (Local)
        app.run_polling()

if __name__ == "__main__":
    main()
