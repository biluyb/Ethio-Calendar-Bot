"""
Main Entry Point for the Ethiopian Calendar Bot.
Configures the Telegram Application, registers command handlers, 
and manages the production/local lifecycle.
"""

import os
import logging
import asyncio
import json
import time
from datetime import datetime, date
from collections import defaultdict
from aiohttp import web
from telegram import Update, BotCommand

# Rate limiting storage: {api_key: [timestamp1, timestamp2, ...]}
# Allow 30 requests per minute per key
API_RATE_LIMITS = defaultdict(list)
RATE_LIMIT_STRICT = 30  # requests
RATE_LIMIT_WINDOW = 60  # seconds

def is_rate_limited(api_key):
    """Check if an API key has exceeded the allowed request rate."""
    now = time.time()
    # Clean up old timestamps outside the window
    API_RATE_LIMITS[api_key] = [t for t in API_RATE_LIMITS[api_key] if now - t < RATE_LIMIT_WINDOW]
    
    if len(API_RATE_LIMITS[api_key]) >= RATE_LIMIT_STRICT:
        return True
    
    API_RATE_LIMITS[api_key].append(now)
    return False

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
    about_command,
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
    api_key_command,
    api_stats_command,
    api_stats_callback,
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
    app.add_handler(CallbackQueryHandler(api_stats_callback, pattern="^(api_dash:|api_revoke_prompt)"))
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

        async def api_convert_handler(request):
            try:
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    api_key = auth_header.split(" ")[1]
                else:
                    api_key = request.query.get("key")
                    
                if not api_key:
                    return web.json_response({"status": "error", "message": "Missing API Key. Include ?key= or Authorization: Bearer header."}, status=401)
                
                from app.db import verify_and_track_api_key
                uid = verify_and_track_api_key(api_key)
                if not uid:
                    return web.json_response({"status": "error", "message": "Invalid API Key."}, status=403)
                
                if is_rate_limited(api_key):
                    return web.json_response({"status": "error", "message": "Rate limit exceeded. Max 30 requests per minute."}, status=429)
                    
                date_str = request.query.get("date")
                to_cal = request.query.get("to_calendar", "").lower()
                
                if not date_str or to_cal not in ["ethiopian", "gregorian"]:
                    return web.json_response({"status": "error", "message": "Missing or invalid parameters. Require 'date' (DD/MM/YYYY) and 'to_calendar' ('ethiopian' or 'gregorian')."}, status=400)
                
                from app.utils import parse_date, greg_to_eth, eth_to_greg, format_eth, format_greg
                parsed = parse_date(date_str)
                if not parsed:
                    return web.json_response({"status": "error", "message": "Invalid date format. Use DD/MM/YYYY."}, status=400)
                    
                d, m, y = parsed
                
                if to_cal == "ethiopian":
                    res_d, res_m, res_y = greg_to_eth(d, m, y)
                    fmt = format_eth(res_d, res_m, res_y)
                else:
                    res_d, res_m, res_y = eth_to_greg(d, m, y)
                    fmt = format_greg(res_d, res_m, res_y)
                    
                return web.json_response({
                    "status": "success",
                    "input": {"date": date_str, "target": to_cal},
                    "result": {
                        "day": res_d,
                        "month": res_m,
                        "year": res_y,
                        "formatted": fmt
                    }
                })
            except ValueError as e:
                return web.json_response({"status": "error", "message": str(e)}, status=400)
            except Exception as e:
                logging.error(f"API error: {e}")
                return web.json_response({"status": "error", "message": "Internal server error"}, status=500)

        async def api_today_handler(request):
            try:
                auth_header = request.headers.get("Authorization", "")
                api_key = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else request.query.get("key")
                
                if not api_key:
                    return web.json_response({"status": "error", "message": "Missing API Key."}, status=401)
                
                from app.db import verify_and_track_api_key
                if not verify_and_track_api_key(api_key):
                    return web.json_response({"status": "error", "message": "Invalid API Key."}, status=403)
                
                if is_rate_limited(api_key):
                    return web.json_response({"status": "error", "message": "Rate limit exceeded."}, status=429)
                
                now = datetime.now()
                from app.utils import greg_to_eth, format_eth, format_greg
                ed, em, ey = greg_to_eth(now.day, now.month, now.year)
                
                return web.json_response({
                    "status": "success",
                    "gregorian": {
                        "day": now.day, "month": now.month, "year": now.year,
                        "formatted": format_greg(now.day, now.month, now.year)
                    },
                    "ethiopian": {
                        "day": ed, "month": em, "year": ey,
                        "formatted": format_eth(ed, em, ey)
                    }
                })
            except Exception as e:
                logging.error(f"API Today error: {e}")
                return web.json_response({"status": "error", "message": "Internal server error"}, status=500)

        async def api_age_handler(request):
            try:
                auth_header = request.headers.get("Authorization", "")
                api_key = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else request.query.get("key")
                
                if not api_key:
                    return web.json_response({"status": "error", "message": "Missing API Key."}, status=401)
                
                from app.db import verify_and_track_api_key
                if not verify_and_track_api_key(api_key):
                    return web.json_response({"status": "error", "message": "Invalid API Key."}, status=403)
                
                if is_rate_limited(api_key):
                    return web.json_response({"status": "error", "message": "Rate limit exceeded."}, status=429)
                
                birth_date_str = request.query.get("birth_date")
                calendar_type = request.query.get("calendar", "gregorian").lower()
                
                if not birth_date_str:
                    return web.json_response({"status": "error", "message": "Missing 'birth_date' parameter."}, status=400)
                
                from app.utils import parse_date, eth_to_greg, calculate_age
                parsed_birth = parse_date(birth_date_str)
                if not parsed_birth:
                    return web.json_response({"status": "error", "message": "Invalid date format. Use DD/MM/YYYY."}, status=400)
                
                bd, bm, by = parsed_birth
                if calendar_type == "ethiopian":
                    # Convert birth date to Gregorian for calculation
                    bd, bm, by = eth_to_greg(bd, bm, by)
                
                birth_dt = date(by, bm, bd)
                today_dt = date.today()
                
                if birth_dt > today_dt:
                    return web.json_response({"status": "error", "message": "Birth date cannot be in the future."}, status=400)
                
                years, months, days = calculate_age(birth_dt, today_dt)
                
                return web.json_response({
                    "status": "success",
                    "age": {"years": years, "months": months, "days": days}
                })
            except ValueError as e:
                return web.json_response({"status": "error", "message": str(e)}, status=400)
            except Exception as e:
                logging.error(f"API Age error: {e}")
                return web.json_response({"status": "error", "message": "Internal server error"}, status=500)

        web_app = web.Application()
        web_app.router.add_get("/", root_handler)
        web_app.router.add_get("/api/convert", api_convert_handler)
        web_app.router.add_get("/api/today", api_today_handler)
        web_app.router.add_get("/api/age", api_age_handler)
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
