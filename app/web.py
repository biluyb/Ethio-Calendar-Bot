"""
HTTP / REST API Layer.

Owns everything the bot exposes over HTTP:
- the landing page at ``/``
- the Telegram webhook endpoint at ``POST /{BOT_TOKEN}``
- the public date-conversion API (``/v1/convert``, ``/v1/today``, ``/v1/age``
  plus the legacy ``/api/*`` aliases), including API-key auth and per-key
  rate limiting.

The aiohttp application is built by :func:`build_web_app`; the Telegram
``Application`` is stashed on ``web_app["telegram_app"]`` so route handlers
can enqueue updates without closure plumbing.
"""

import asyncio
import logging
import time
from collections import defaultdict
from datetime import date, datetime

from aiohttp import web
from telegram import Update

from app.config import BOT_TOKEN
from app.db import get_eth_datetime, get_eth_today

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


def standard_response(success, data=None, error=None, status=200, meta=None):
    """Standardized JSON response format for all API endpoints."""
    body = {"success": success}
    if data is not None: body["data"] = data
    if error is not None: body["error"] = error
    if meta is not None: body["meta"] = meta
    else: body["meta"] = {"timestamp": datetime.now().isoformat()}
    return web.json_response(body, status=status)


async def get_api_user(request):
    """Helper to authenticate API keys from header or query."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        key = auth_header.split(" ")[1]
    else:
        key = request.query.get("key")

    if not key: return None, None

    from app.db import verify_and_track_api_key
    # Blocking DB call — run off the event loop so API handlers don't stall
    uid = await asyncio.to_thread(verify_and_track_api_key, key)
    return uid, key


async def api_convert_handler(request):
    user_data = await get_api_user(request)
    uid, key = user_data
    if not uid:
        return standard_response(False, error={"code": "UNAUTHORIZED", "message": "Missing or invalid API Key."}, status=401)

    if is_rate_limited(key):
        return standard_response(False, error={"code": "RATE_LIMIT_EXCEEDED", "message": "Max 30 requests per minute."}, status=429)

    date_str = request.query.get("date")
    to_cal = (request.query.get("to") or request.query.get("to_calendar", "")).lower()

    if not date_str or to_cal not in ["ethiopian", "gregorian", "eth", "gc"]:
        return standard_response(False, error={"code": "INVALID_PARAMS", "message": "Require 'date' (DD/MM/YYYY) and 'to' ('ethiopian' or 'gregorian')."}, status=400)

    # Normalize to_cal
    if to_cal == "eth": to_cal = "ethiopian"
    if to_cal == "gc": to_cal = "gregorian"

    from app.utils import parse_date, greg_to_eth, eth_to_greg, format_eth, format_greg
    try:
        parsed = parse_date(date_str)
        if not parsed:
            return standard_response(False, error={"code": "INVALID_DATE_FORMAT", "message": "Use DD/MM/YYYY."}, status=400)

        d, m, y = parsed
        if to_cal == "ethiopian":
            res_d, res_m, res_y = greg_to_eth(d, m, y)
            fmt = format_eth(res_d, res_m, res_y)
        else:
            res_d, res_m, res_y = eth_to_greg(d, m, y)
            fmt = format_greg(res_d, res_m, res_y)

        return standard_response(True, data={
            "input": {"date": date_str, "target": to_cal},
            "result": {"day": res_d, "month": res_m, "year": res_y, "formatted": fmt}
        })
    except ValueError as e:
        return standard_response(False, error={"code": "VALIDATION_ERROR", "message": str(e)}, status=400)
    except Exception as e:
        logging.error(f"API error: {e}")
        return standard_response(False, error={"code": "SERVER_ERROR", "message": "Internal server error"}, status=500)


async def api_today_handler(request):
    user_data = await get_api_user(request)
    uid, key = user_data
    if not uid:
        return standard_response(False, error={"code": "UNAUTHORIZED", "message": "Invalid API Key."}, status=401)

    if is_rate_limited(key):
        return standard_response(False, error={"code": "RATE_LIMIT_EXCEEDED", "message": "Rate limit exceeded."}, status=429)

    try:
        now = get_eth_datetime()
        from app.utils import greg_to_eth, format_eth, format_greg
        ed, em, ey = greg_to_eth(now.day, now.month, now.year)

        return standard_response(True, data={
            "gregorian": {"day": now.day, "month": now.month, "year": now.year, "formatted": format_greg(now.day, now.month, now.year)},
            "ethiopian": {"day": ed, "month": em, "year": ey, "formatted": format_eth(ed, em, ey)}
        })
    except Exception as e:
        logging.error(f"API Today error: {e}")
        return standard_response(False, error={"code": "SERVER_ERROR", "message": "Internal server error"}, status=500)


async def api_age_handler(request):
    user_data = await get_api_user(request)
    uid, key = user_data
    if not uid:
        return standard_response(False, error={"code": "UNAUTHORIZED", "message": "Invalid API Key."}, status=401)

    if is_rate_limited(key):
        return standard_response(False, error={"code": "RATE_LIMIT_EXCEEDED", "message": "Rate limit exceeded."}, status=429)

    birth_date_str = request.query.get("birth_date") or request.query.get("date")
    calendar_type = (request.query.get("calendar") or request.query.get("from", "gregorian")).lower()

    if not birth_date_str:
        return standard_response(False, error={"code": "INVALID_PARAMS", "message": "Missing 'birth_date' (DD/MM/YYYY)."}, status=400)

    from app.utils import parse_date, eth_to_greg, calculate_age
    try:
        parsed_birth = parse_date(birth_date_str)
        if not parsed_birth:
            return standard_response(False, error={"code": "INVALID_DATE_FORMAT", "message": "Use DD/MM/YYYY."}, status=400)

        bd, bm, by = parsed_birth
        if calendar_type in ["ethiopian", "eth"]:
            bd, bm, by = eth_to_greg(bd, bm, by)

        birth_dt = date(by, bm, bd)
        today_dt = get_eth_today()

        if birth_dt > today_dt:
            return standard_response(False, error={"code": "FUTURE_DATE", "message": "Birth date cannot be in the future."}, status=400)

        years, months, days = calculate_age(birth_dt, today_dt)
        return standard_response(True, data={"years": years, "months": months, "days": days})
    except ValueError as e:
        return standard_response(False, error={"code": "VALIDATION_ERROR", "message": str(e)}, status=400)
    except Exception as e:
        logging.error(f"API Age error: {e}")
        return standard_response(False, error={"code": "SERVER_ERROR", "message": "Internal server error"}, status=500)


LANDING_HTML = """
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
        <a href="https://t.me/pagumebot" class="btn">Launch on Telegram</a>
    </div>
</body>
</html>
"""


async def root_handler(request):
    return web.Response(text=LANDING_HTML, content_type="text/html")


async def webhook_handler(request):
    """Feeds a Telegram webhook update into the bot's update queue."""
    app = request.app["telegram_app"]
    try:
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.update_queue.put(update)
        return web.Response(status=200)
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return web.Response(status=500)


def build_web_app(app) -> web.Application:
    """Builds the aiohttp application with all HTTP/API routes.

    ``app`` is the running ``telegram.ext.Application``; it is stashed on the
    aiohttp app so the webhook handler can enqueue updates.
    """
    web_app = web.Application()
    web_app["telegram_app"] = app

    web_app.router.add_get("/", root_handler)

    # v1 Standard Routes
    web_app.router.add_get("/v1/convert", api_convert_handler)
    web_app.router.add_get("/v1/today", api_today_handler)
    web_app.router.add_get("/v1/age", api_age_handler)

    # Legacy Support (pointing to the improved logic)
    web_app.router.add_get("/api/convert", api_convert_handler)
    web_app.router.add_get("/api/today", api_today_handler)
    web_app.router.add_get("/api/age", api_age_handler)

    # Webhook endpoint — the token in the path acts as a shared secret
    web_app.router.add_post(f"/{BOT_TOKEN}", webhook_handler)

    return web_app
