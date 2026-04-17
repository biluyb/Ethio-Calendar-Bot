import html
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .common import (
    track_activity, get_lang, send_error, get_menu, check_blocked, track_group,
    EN_DAYS, EN_MONTHS, AM_DAYS, AM_MONTHS, INVITE_IMAGE_PATH, REDIRECT_IMAGE_URL
)
from .user import today, share_command
from .api import api_key_command, api_stats_command
from app.db import (
    set_lang, get_lang, is_admin_db, revoke_api_key_db, get_admins_db, 
    get_user_by_id, get_user_by_username
)
from app.utils import eth_to_greg, greg_to_eth, calculate_age
from app.config import ADMIN_IDS

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update): return
    track_activity(update)
    try:
        if update.effective_chat.type in ["group", "supergroup"]:
            if update.message and update.message.text:
                uid = update.effective_user.id
                lang = get_lang(uid)
                track_group(update)
                dm_url = f"https://t.me/{context.bot.username}?start=from_group"
                kb = [[InlineKeyboardButton("▶️ ቦቱን ክፈት" if lang == "am" else "▶️ Open Bot", url=dm_url)]]
                msg = "<b>ጳጉሜ ቦት</b>" if lang == "am" else "<b>Pagume Bot</b>"
                try:
                    with open(INVITE_IMAGE_PATH, "rb") as p: await update.message.reply_photo(p, caption=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
                except: await update.message.reply_photo(REDIRECT_IMAGE_URL, caption=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
            return

        if not update.message or not update.message.text: return
        uid = update.effective_user.id
        text = update.message.text.strip()
        lang = get_lang(uid)

        if await process_menu_commands(update, context, text, uid, lang): return
        
        mode = context.user_data.get("mode")
        if not mode: return

        if mode == "contact_admin": return await handle_admin_contact_message(update, context)
        if mode.startswith("rep_"): return await handle_admin_reply_to_user(update, context)
        if mode == "admin_dm_send": return await handle_admin_dm_send(update, context)
        if mode == "admin_api_revoke_input":
            if revoke_api_key_db(int(text)) if text.isdigit() else False: await update.message.reply_text("✅ Revoked")
            else: await update.message.reply_text("❌ Failed")
            context.user_data.pop("mode", None)
            return

        # Date processing
        try:
            d, m, y = map(int, text.replace("-", "/").split("/"))
        except: return await update.message.reply_text("❌ Invalid format. DD/MM/YYYY")

        if mode == "g2e": await process_g2e(update, context, d, m, y, lang)
        elif mode == "e2g": await process_e2g(update, context, d, m, y, lang)
        elif mode.startswith("age_calc_"): await process_age_calc(update, context, d, m, y, lang, mode)

    except Exception as e: await send_error(update, context, e, "handle")

async def process_menu_commands(update, context, text, uid, lang):
    if text == "🇺🇸 English":
        set_lang(uid, "en")
        await update.message.reply_text("✅ Set to English", reply_markup=get_menu(uid, "en"))
        return True
    if text == "🇪🇹 አማርኛ":
        set_lang(uid, "am")
        await update.message.reply_text("✅ ወደ አማርኛ ተቀይሯል", reply_markup=get_menu(uid, "am"))
        return True
    if text in ["📅 Today", "📅 ዛሬ"]: await today(update, context); return True
    if text in ["🌐 Language", "🌐 ቋንቋ"]:
        await update.message.reply_text("Choose language", reply_markup=ReplyKeyboardMarkup([["🇺🇸 English", "🇪🇹 አማርኛ"]], resize_keyboard=True))
        return True
    if text in ["📩 Contact Admin", "📩 አድሚኑን ያግኙ"]:
        context.user_data["mode"] = "contact_admin"
        kb = [[InlineKeyboardButton("📩 Contact Admin" if lang=="en" else "📩 አድሚኑን ያግኙ", callback_data="contact_admin_request")]]
        await update.message.reply_text("Type message below:", reply_markup=InlineKeyboardMarkup(kb))
        return True
    if text in ["🎂 Age Calculator", "🎂 የዕድሜ ስሌት"]:
        kb = [[InlineKeyboardButton("Gregorian", callback_data="age_mode_gc"), InlineKeyboardButton("Ethiopian", callback_data="age_mode_et")]]
        await update.message.reply_text("Choose calendar:", reply_markup=InlineKeyboardMarkup(kb))
        return True
    if text in ["🤝 Invite Friends", "🤝 ጓደኞችን ይጋብዙ"]: await share_command(update, context); return True
    if text in ["📅 Gregorian ➜ Ethiopian", "📅 ከፈረንጅ ወደ ኢትዮጵያ"]: context.user_data["mode"] = "g2e"; await update.message.reply_text("Enter DD/MM/YYYY:"); return True
    if text in ["📆 Ethiopian ➜ Gregorian", "📆 ከኢትዮጵያ ወደ ፈረንጅ"]: context.user_data["mode"] = "e2g"; await update.message.reply_text("Enter DD/MM/YYYY:"); return True
    if text in ["🔐 API (Developer)", "🔐 ኤፒአይ (Developer)"]: await api_key_command(update, context); return True
    if text in ["📊 API Stats", "📊 ኤፒአይ ስታቲስቲክስ"]: await api_stats_command(update, context); return True
    return False

async def process_g2e(update, context, d, m, y, lang):
    try:
        ed, em, ey = greg_to_eth(d, m, y)
        await update.message.reply_text(f"🇪🇹 {ed}-{em}-{ey}", reply_markup=get_menu(update.effective_user.id, lang))
        context.user_data.pop("mode", None)
    except Exception as e:
        await handle_date_error(update, e, d, m, y, lang)

async def process_e2g(update, context, d, m, y, lang):
    try:
        gd, gm, gy = eth_to_greg(d, m, y)
        await update.message.reply_text(f"🇺🇸 {gd:02}-{gm:02}-{gy}", reply_markup=get_menu(update.effective_user.id, lang))
        context.user_data.pop("mode", None)
    except Exception as e:
        await handle_date_error(update, e, d, m, y, lang)

async def process_age_calc(update, context, d, m, y, lang, mode):
    try:
        now = datetime.now()
        gd, gm, gy = (d, m, y) if mode == "age_calc_gc" else eth_to_greg(d, m, y)
        birth = datetime(gy, gm, gd)
        if birth > now:
            msg = "❌ Future date" if lang=="en" else "❌ የልደት ቀን ወደፊት መሆን አይችልም!"
            return await update.message.reply_text(msg)
        yrs, mos, dys = calculate_age(birth, now)
        await update.message.reply_text(f"🎂 {yrs}Y {mos}M {dys}D", reply_markup=get_menu(update.effective_user.id, lang))
        context.user_data.pop("mode", None)
    except Exception as e:
        await handle_date_error(update, e, d, m, y, lang)

async def handle_date_error(update, e, d, m, y, lang):
    err = str(e)
    if "Pagume in" in err:
        lim = 6 if "1-6" in err else 5
        msg = f"❌ Pagume only has {lim} days in {y}." if lang=="en" else f"❌ ጳጉሜ በ {y} ዓ.ም {lim} ቀናት ብቻ ነው ያላት።"
    elif "1-30 days" in err:
        msg = f"❌ Month {m} only has 30 days." if lang=="en" else f"❌ ወር {m} 30 ቀናት ብቻ ነው ያለው።"
    elif "month must be" in err.lower():
        msg = "❌ Month must be 1-12." if lang=="en" else "❌ ወር ከ 1 እስከ 12 መሆን አለበት።"
    elif "day is out of range" in err:
        msg = "❌ Invalid day for this month." if lang=="en" else "❌ ያስገቡት ቀን ለዛ ወር ትክክል አይደለም።"
    else:
        msg = "❌ Invalid date range." if lang=="en" else "❌ ትክክለኛ ያልሆነ ቀን።"
    await update.message.reply_text(msg)

async def handle_admin_contact_message(update, context):
    uid, user = update.effective_user.id, update.effective_user
    msg = f"✉️ <b>Message from</b> {user.full_name} (<code>{uid}</code>)\n\n{html.escape(update.message.text)}"
    admins = set(get_admins_db()) | set(ADMIN_IDS)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Reply", callback_data=f"admin_reply_{uid}")]])
    for aid in admins:
        try: await context.bot.send_message(chat_id=aid, text=msg, parse_mode="HTML", reply_markup=kb)
        except: pass
    await update.message.reply_text("✅ Sent to admin")
    context.user_data.pop("mode", None)

async def admin_reply_callback(update, context):
    tid = update.callback_query.data.replace("admin_reply_", "")
    context.user_data["mode"] = f"rep_{tid}"
    await update.callback_query.message.reply_text(f"✍️ Replying to {tid}:")
    await update.callback_query.answer()

async def handle_admin_reply_to_user(update, context):
    tid = int(context.user_data["mode"].replace("rep_", ""))
    await context.bot.send_message(chat_id=tid, text=f"📨 <b>Admin Reply:</b>\n\n{update.message.text}", parse_mode="HTML")
    await update.message.reply_text("✅ Reply sent")
    context.user_data.pop("mode", None)

async def handle_admin_dm_send(update, context):
    tid, tname = context.user_data["target_uid"], context.user_data["target_name"]
    await context.bot.send_message(chat_id=tid, text=f"📨 <b>Admin Message:</b>\n\n{update.message.text}", parse_mode="HTML")
    await update.message.reply_text(f"✅ Sent to {tname}")
    context.user_data.pop("mode", None)

async def unknown_command(update, context):
    await update.message.reply_text("❌ Unknown command. Use /help", reply_markup=get_menu(update.effective_user.id, get_lang(update.effective_user.id)))
