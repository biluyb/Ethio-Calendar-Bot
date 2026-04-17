"""
Main Entry Point for the Ethiopian Calendar Bot.
Configures the Telegram Application, registers command handlers, 
and manages the production/local lifecycle.
"""

import os
import logging
import asyncio
import json
from aiohttp import web
from telegram import Update, BotCommand
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
    health_url,
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

async def main():
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
    app.add_handler(CommandHandler("health_url", health_url))
    
    # Callback Handlers (Inline Buttons)
    app.add_handler(CallbackQueryHandler(users_callback, pattern="^(u:|ud:|toggle_block_user:|send_msg_init:)"))
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
        # Production: Custom aiohttp handling for root landing page + webhook
        await app.initialize()
        await app.start()

        async def root_handler(request):
            html = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Pagume Bot | Ethiopian Calendar</title>
                <style>
                    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 40px 20px; text-align: center; }
                    .card { background: #f9f9f9; border-radius: 12px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                    h1 { color: #2c3e50; margin-bottom: 10px; }
                    .features { text-align: left; display: inline-block; margin: 20px 0; }
                    .features li { margin-bottom: 8px; list-style: none; }
                    .btn { display: inline-block; background: #0088cc; color: white; padding: 12px 24px; text-decoration: none; border-radius: 25px; font-weight: bold; margin-top: 20px; }
                    .status { color: #27ae60; font-weight: bold; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>📅 Pagume Bot</h1>
                    <p class="status">● System Active & Online</p>
                    <p>The most advanced Ethiopian Calendar & Date Converter on Telegram.</p>
                    
                    <ul class="features">
                        <li>✅ <b>Precise Conversion:</b> Gregorian ↔ Ethiopian.</li>
                        <li>✅ <b>Bilingual:</b> English & Amharic native support.</li>
                        <li>✅ <b>Referral Rewards:</b> Advanced ranking system.</li>
                        <li>✅ <b>Admin Suite:</b> Real-time user management.</li>
                    </ul>
                    <br>
                    <a href="https://t.me/EthioCalendarBot" class="btn">Launch on Telegram</a>
                </div>
            </body>
            </html>
            """
            return web.Response(text=html, content_type="text/html")

        async def webhook_handler(request):
            try:
                data = await request.json()
                update = Update.de_json(data, app.bot)
                await app.update_queue.put(update)
                return web.Response(status=200)
            except Exception as e:
                logging.error(f"Webhook error: {e}")
                return web.Response(status=500)

        web_app = web.Application()
        web_app.router.add_get("/", root_handler)
        web_app.router.add_post(f"/{BOT_TOKEN}", webhook_handler)

        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        
        print(f"🌍 Web server active on port {PORT}")
        print(f"🔗 Health check at {WEBHOOK_URL}/")
        
        # Keep alive
        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            await app.stop()
            await app.shutdown()
    else:
        # Development: Polling Mode
        app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
