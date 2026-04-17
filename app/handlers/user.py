import html
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommandScopeChat
from telegram.ext import ContextTypes
from .common import (
    get_menu, track_activity, track_group, check_blocked, send_error,
    EN_DAYS, EN_MONTHS, AM_DAYS, AM_MONTHS, INVITE_IMAGE_PATH, REDIRECT_IMAGE_URL,
    SUPER_ADMIN_CMDS, ADMIN_CMDS
)
from app.db import (
    get_lang, set_lang, get_user_details, get_top_referrers, get_referrers_count,
    is_admin_db, register_user
)
from app.utils import greg_to_eth
from app.texts import INFO_EN, INFO_AM
from app.config import ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update): return
    try:
        uid = update.effective_user.id
        if update.effective_chat.type in ["group", "supergroup"]:
            track_group(update)
            track_activity(update, "/start (Group)")
            lang = get_lang(uid)
            dm_url = f"https://t.me/{context.bot.username}?start=from_group"
            kb = [[InlineKeyboardButton("▶️ ቦቱን ክፈት" if lang == "am" else "▶️ Open Bot", url=dm_url)]]
            msg = "<b>ጳጉሜ ቦት</b>\n<i> የኢትዮጵያ ቀን መቁጠሪያ።</i>" if lang == "am" else "<b>Pagume Bot</b>\n<i>Ethiopian Calendar & Date Converter.</i>"
            try:
                with open(INVITE_IMAGE_PATH, "rb") as p: await update.message.reply_photo(p, caption=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
            except: await update.message.reply_photo(REDIRECT_IMAGE_URL, caption=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
            return

        user = update.effective_user
        referred_by = int(context.args[0]) if context.args and context.args[0].isdigit() and int(context.args[0]) != uid else None
        is_new = register_user(uid, user.username or user.full_name or str(uid), full_name=user.full_name, last_command="/start", referred_by=referred_by)
        
        if is_new and referred_by:
            try:
                ref_lang = get_lang(referred_by)
                u_det = get_user_details(referred_by)
                count = u_det[10] if u_det else 1
                txt = f"🎉 <b>እንኳን ደስ አለዎት!</b>\n\n<b>{user.full_name}</b> ተቀላቅሏል።\n📊 ብዛት: {count}" if ref_lang == "am" else f"🎉 <b>New Referral!</b>\n\n<b>{user.full_name}</b> joined.\n📊 Total: {count}"
                await context.bot.send_message(chat_id=referred_by, text=txt, parse_mode="HTML")
            except: pass

        lang = get_lang(uid)
        await update.message.reply_text("📅 Welcome / እንኳን ደህና መጡ", reply_markup=get_menu(uid, lang))
        await refresh_user_commands(context.bot, uid)
    except Exception as e: await send_error(update, context, e, "start")

async def refresh_user_commands(bot, uid):
    try:
        scope = BotCommandScopeChat(chat_id=uid)
        if uid in ADMIN_IDS: await bot.set_my_commands(SUPER_ADMIN_CMDS, scope=scope)
        elif is_admin_db(uid): await bot.set_my_commands(ADMIN_CMDS, scope=scope)
        else: await bot.delete_my_commands(scope=scope)
    except: pass

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id
        track_activity(update, "Command: /today")
        lang = get_lang(uid)
        now = datetime.now()
        ed, em, ey = greg_to_eth(now.day, now.month, now.year)
        msg = f"Today\n\n🇺🇸 {now.day:02}-{now.month:02}-{now.year} | {EN_DAYS[now.weekday()]}\n🇪🇹 {ed}-{em}-{ey} | {AM_DAYS[now.weekday()]}"
        await update.message.reply_text(msg, reply_markup=get_menu(uid, lang))
    except Exception as e: await send_error(update, context, e, "today")

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id
        new_lang = "am" if get_lang(uid) == "en" else "en"
        set_lang(uid, new_lang)
        await update.message.reply_text("✅ Language changed" if new_lang=="en" else "✅ ቋንቋ ተቀይሯል", reply_markup=get_menu(uid, new_lang))
    except Exception as e: await send_error(update, context, e, "lang")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        lang = get_lang(update.effective_user.id)
        await update.message.reply_text(INFO_AM if lang=="am" else INFO_EN, parse_mode="HTML")
    except Exception as e: await send_error(update, context, e, "info")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        txt = "<b>Bot Information:</b>\n\nDeveloped by ShademT" if lang=="en" else "<b>የቦት መረጃ</b>\n\nበ ShademT የተሰራ"
        kb = [[InlineKeyboardButton("📩 Contact Admin" if lang=="en" else "📩 አድሚኑን ያግኙ", callback_data="contact_admin_request")],
              [InlineKeyboardButton("➕ Add to Group" if lang=="en" else "➕ ወደ ግሩፕ አስገባ", url=f"https://t.me/{context.bot.username}?startgroup=true")]]
        await update.message.reply_text(txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e: await send_error(update, context, e, "about")

async def share_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        url = f"https://t.me/{context.bot.username}?start={uid}"
        txt = f"<b>Pagume Bot</b>\n\nInvite link: {url}" if lang=="en" else f"<b>ጳጉሜ ቦት</b>\n\nመጋበዣ ሊንክ: {url}"
        try:
            with open(INVITE_IMAGE_PATH, "rb") as p: await update.message.reply_photo(p, caption=txt, parse_mode="HTML")
        except: await update.message.reply_text(txt, parse_mode="HTML")
    except Exception as e: await send_error(update, context, e, "share")

async def ranks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_ranks_page(update, context, 0)

async def ranks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_activity(update)
    page = int(update.callback_query.data.split(":")[1])
    await send_ranks_page(update, context, page)

async def send_ranks_page(update, context, page):
    try:
        per = 10
        users = get_top_referrers(limit=per, offset=page*per)
        total = get_referrers_count()
        lang = get_lang(update.effective_user.id)
        msg = "🏆 <b>Leaderboard</b>\n\n" if lang=="en" else "🏆 <b>ጥሩ ጋባዦች</b>\n\n"
        if not users: msg += "No referrals yet."
        for i, (ruid, uname, count) in enumerate(users, 1 + page*per):
            msg += f"{i}. <b>{uname}</b> — {count} invites\n"
        btns = []
        if page > 0: btns.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"r:{page-1}"))
        if (page+1)*per < total: btns.append(InlineKeyboardButton("Next ➡️", callback_data=f"r:{page+1}"))
        markup = InlineKeyboardMarkup([btns]) if btns else None
        if update.message: await update.message.reply_text(msg, parse_mode="HTML", reply_markup=markup)
        else: await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=markup)
    except Exception as e: await send_error(update, context, e, "ranks_page")
