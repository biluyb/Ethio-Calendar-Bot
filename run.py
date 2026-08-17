"""
Main Entry Point for the Ethiopian Calendar Bot.
Configures the Telegram Application and manages the production/local lifecycle.

The heavy lifting lives in dedicated modules:
- ``app/handlers`` — all command/callback/message handlers + ``register_handlers``
- ``app/web.py`` — landing page, webhook endpoint, and the public REST API
- ``app/scheduler.py`` — background reminder loop
- ``app/db`` — data layer
"""

import asyncio
import os

from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder

from app.config import BOT_TOKEN, ADMIN_IDS
from app.db import init_db, add_admin_db, get_admins_db
from app.handlers import USER_CMDS, refresh_user_commands, register_handlers
from app.scheduler import start_scheduler
from app.web import build_web_app

# Environment Overrides
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")


async def main():
    """
    Initializes the system and starts the bot.
    Handles DB setup, role synchronization, handler registration, and the
    webhook (production) vs polling (development) lifecycle.
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
        """Set default commands for all users and specialized ones for admins."""
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

    # Start background reminder scheduler
    start_scheduler(app)

    # 3. Handler Registration
    register_handlers(app)

    # 4. Lifecycle Execution
    print(f"Bot starting (Environment: {'Production' if WEBHOOK_URL else 'Development'})...")

    if WEBHOOK_URL:
        # Production: aiohttp server for landing page + webhook + REST API
        await app.initialize()
        await app.start()

        web_app = build_web_app(app)
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
            await site.stop()
            await runner.cleanup()
            await app.stop()
            await app.shutdown()
    else:
        # Development: Polling Mode
        # Explicitly request update types so my_chat_member (bot block/unblock
        # tracking via ChatMemberHandler) is delivered — Telegram omits
        # chat_member-family updates unless they are whitelisted.
        app.run_polling(allowed_updates=[
            Update.MESSAGE,
            Update.EDITED_MESSAGE,
            Update.CALLBACK_QUERY,
            Update.MY_CHAT_MEMBER,
        ])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
