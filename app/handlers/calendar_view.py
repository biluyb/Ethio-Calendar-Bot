"""
Interactive Ethiopian Calendar & Reminder System
Provides:
- 10-year navigation (current year ± 5 years)
- Pixel-perfect Inline Keyboard grid with interactive day selection
- Integrated Reminder System: Click any date to add a reminder/memo
- Automated background notifications on due date
- Ethiopian public holidays, closures, and special observances
- Evangelist cycle and Gregorian date alignment
- Full bilingual support (Amharic / English)
"""

import html
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from app.db import get_lang
from app.db.reminder_db import add_reminder, get_user_reminders, get_user_day_reminders, get_month_user_reminder_days, delete_reminder
from app.utils import greg_to_eth, eth_to_greg, is_leap_eth
from app.holidays import get_month_holidays, get_day_type, TYPE_EMOJI, TYPE_LABEL
from .common import track_activity, send_error, get_menu

# ─── Ethiopian Calendar Constants ────────────────────────────────────────────

ETH_MONTHS_AM = [
    "መስከረም", "ጥቅምት", "ኅዳር", "ታኅሣሥ",
    "ጥር", "የካቲት", "መጋቢት", "ሚያዝያ",
    "ግንቦት", "ሰኔ", "ሐምሌ", "ነሐሴ", "ጳጉሜ"
]

ETH_MONTHS_EN = [
    "Meskerem", "Tikimt", "Hidar", "Tahsas",
    "Tir", "Yekatit", "Megabit", "Miyazia",
    "Ginbot", "Sene", "Hamle", "Nehase", "Pagume"
]

WEEKDAYS_AM = ["ሰኞ", "ማክ", "ረቡ", "ሐሙ", "አርብ", "ቅዳ", "እሁ"]
WEEKDAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def get_current_eth_date():
    """Returns today's Ethiopian date as (day, month, year)."""
    now = datetime.now()
    return greg_to_eth(now.day, now.month, now.year)


def eth_days_in_month(eth_month: int, eth_year: int) -> int:
    """Returns number of days in an Ethiopian month."""
    if eth_month <= 12:
        return 30
    return 6 if is_leap_eth(eth_year) else 5


def get_weekday_of_eth_day1(eth_month: int, eth_year: int) -> int:
    """Returns Python weekday (Mon=0, Sun=6) of day 1 of a given Ethiopian month."""
    gd, gm, gy = eth_to_greg(1, eth_month, eth_year)
    return date(gy, gm, gd).weekday()


def get_evangelist(eth_year: int) -> dict | None:
    """Returns the evangelist cycle name for a given Ethiopian year."""
    amete_alem = eth_year + 5500
    remainder = amete_alem % 4
    mapping = {
        1: {"am": "ማቴዎስ", "en": "Matthew"},
        2: {"am": "ማርቆስ", "en": "Mark"},
        3: {"am": "ሉቃስ (ዘመነ ዕርገት)", "en": "Luke (Leap)"},
        0: {"am": "ዮሐንስ", "en": "John"},
    }
    return mapping.get(remainder)


# ─── Calendar Builder Functions ─────────────────────────────────────────────

def build_calendar_view(eth_year: int, eth_month: int, user_id: int, lang: str):
    """
    Builds the monthly calendar message text AND perfect inline keyboard layout.
    """
    today_ed, today_em, today_ey = get_current_eth_date()
    month_name_am = ETH_MONTHS_AM[eth_month - 1]
    month_name_en = ETH_MONTHS_EN[eth_month - 1]
    evangelist = get_evangelist(eth_year)

    era_label_am = f"ዘመነ {evangelist['am']}" if evangelist else ""
    era_label_en = f"Year of {evangelist['en']}" if evangelist else ""

    if lang == "am":
        header = (
            f"📅 <b>{month_name_am} {eth_year} ዓ.ም</b>\n"
            f"<i>{era_label_am}</i>\n"
        )
    else:
        header = (
            f"📅 <b>{month_name_en}, {eth_year} E.C.</b>\n"
            f"<i>{era_label_en}</i>\n"
        )

    # Gregorian start date
    try:
        gd1, gm1, gy1 = eth_to_greg(1, eth_month, eth_year)
        from .common import EN_MONTHS
        greg_start = f"{EN_MONTHS[gm1-1]} {gd1}, {gy1}"
        if lang == "am":
            header += f"📆 <i>ፈረንጅ: {greg_start}</i>\n"
        else:
            header += f"📆 <i>Starts: {greg_start} (GC)</i>\n"
    except Exception:
        pass

    header += "━━━━━━━━━━━━━━━━━\n"

    # Fetch holidays & user reminders for the month
    holidays = get_month_holidays(eth_month, eth_year)
    user_rem_days = get_month_user_reminder_days(user_id, eth_year, eth_month)

    # Monospaced text preview legend
    legend = (
        "📍 = ዛሬ | 🔴 = በዓል | 🔔 = ማስታወሻ\n<i>ቀን በመጫን ማስታወሻ ማስቀመጥ ይችላሉ!</i>"
        if lang == "am" else
        "📍 = Today | 🔴 = Holiday | 🔔 = Reminder\n<i>Click any date to add a reminder!</i>"
    )

    # Events list below
    event_list = ""
    if holidays:
        if lang == "am":
            event_list += "\n📌 <b>የዚህ ወር በዓላት:</b>\n"
        else:
            event_list += "\n📌 <b>This Month's Events:</b>\n"
        for day, info in sorted(holidays.items()):
            emoji = TYPE_EMOJI.get(info["type"], "🔴")
            name = info["am"] if lang == "am" else info["en"]
            mname = month_name_am if lang == "am" else month_name_en
            event_list += f"{emoji} <b>{mname} {day}</b> — {name}\n"

    full_text = f"{header}\n{legend}\n{event_list}"

    # Build Perfect Inline Keyboard Grid
    keyboard = []

    # Row 0: Weekday Headers (7 columns)
    wd_row = WEEKDAYS_AM if lang == "am" else WEEKDAYS_EN
    header_buttons = [InlineKeyboardButton(d, callback_data="cal_ignore") for d in wd_row]
    keyboard.append(header_buttons)

    total_days = eth_days_in_month(eth_month, eth_year)
    start_weekday = get_weekday_of_eth_day1(eth_month, eth_year)

    curr_row = []
    # Fill leading empty slots
    for _ in range(start_weekday):
        curr_row.append(InlineKeyboardButton(" ", callback_data="cal_ignore"))

    for d in range(1, total_days + 1):
        is_today = (d == today_ed and eth_month == today_em and eth_year == today_ey)
        has_rem = d in user_rem_days
        holiday = holidays.get(d)

        # Priority badge formatting for button label
        if is_today:
            label = f"📍{d}"
        elif has_rem:
            label = f"🔔{d}"
        elif holiday:
            emoji = TYPE_EMOJI.get(holiday["type"], "🔴")
            label = f"{emoji}{d}"
        else:
            label = f"{d:2d}"

        curr_row.append(InlineKeyboardButton(label, callback_data=f"cal_day:{eth_year}:{eth_month}:{d}"))

        if len(curr_row) == 7:
            keyboard.append(curr_row)
            curr_row = []

    if curr_row:
        while len(curr_row) < 7:
            curr_row.append(InlineKeyboardButton(" ", callback_data="cal_ignore"))
        keyboard.append(curr_row)

    # Navigation controls row
    today_ed, today_em, today_ey = get_current_eth_date()
    min_year = today_ey - 1
    max_year = today_ey + 10

    prev_month, prev_year = (eth_month - 1, eth_year) if eth_month > 1 else (13, eth_year - 1)
    next_month, next_year = (eth_month + 1, eth_year) if eth_month < 13 else (1, eth_year + 1)

    nav_row = []
    if prev_year >= min_year:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"cal:{prev_year}:{prev_month}"))
    
    m_label = month_name_am if lang == "am" else month_name_en
    nav_row.append(InlineKeyboardButton(f"📅 {m_label} {eth_year}", callback_data=f"cal_months:{eth_year}"))

    if next_year <= max_year:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"cal:{next_year}:{next_month}"))

    keyboard.append(nav_row)

    # Quick year jump row
    year_row = []
    for delta in [-2, -1, 0, 1, 2]:
        yr = eth_year + delta
        if min_year <= yr <= max_year:
            btn_txt = f"•{yr}•" if yr == eth_year else str(yr)
            year_row.append(InlineKeyboardButton(btn_txt, callback_data=f"cal:{yr}:{eth_month}"))
    keyboard.append(year_row)

    # Bottom action buttons: Today & My Reminders
    bottom_row = []
    if not (eth_year == today_ey and eth_month == today_em):
        t_txt = "📍 ዛሬ" if lang == "am" else "📍 Today"
        bottom_row.append(InlineKeyboardButton(t_txt, callback_data=f"cal:{today_ey}:{today_em}"))

    rem_txt = "🔔 የማስታወሻዎች ዝርዝር" if lang == "am" else "🔔 My Reminders"
    bottom_row.append(InlineKeyboardButton(rem_txt, callback_data="my_reminders"))
    keyboard.append(bottom_row)

    return full_text, InlineKeyboardMarkup(keyboard)


# ─── Day Details & Reminder View ───────────────────────────────────────────

def build_day_detail_view(eth_year: int, eth_month: int, eth_day: int, user_id: int, lang: str):
    """
    Builds the detailed view when a user clicks a specific date.
    Shows: Ethiopian date, Gregorian equivalent, Holidays, User Reminders, and Add/Delete actions.
    """
    m_am = ETH_MONTHS_AM[eth_month - 1]
    m_en = ETH_MONTHS_EN[eth_month - 1]
    
    # Gregorian date conversion
    gd, gm, gy = eth_to_greg(eth_day, eth_month, eth_year)
    from .common import EN_MONTHS
    greg_str = f"{EN_MONTHS[gm-1]} {gd}, {gy}"

    # Day of week
    wd_idx = date(gy, gm, gd).weekday()
    wd_am = WEEKDAYS_AM[wd_idx]
    wd_en = WEEKDAYS_EN[wd_idx]

    if lang == "am":
        text = (
            f"📅 <b>{wd_am}፣ {m_am} {eth_day} ቀን {eth_year} ዓ.ም</b>\n"
            f"📆 ፈረንጅ፦ <b>{greg_str}</b>\n"
            f"━━━━━━━━━━━━━━━━━\n\n"
        )
    else:
        text = (
            f"📅 <b>{wd_en}, {m_en} {eth_day}, {eth_year} E.C.</b>\n"
            f"📆 Gregorian: <b>{greg_str}</b>\n"
            f"━━━━━━━━━━━━━━━━━\n\n"
        )

    # Holiday check
    holidays = get_month_holidays(eth_month, eth_year)
    holiday = holidays.get(eth_day)
    if holiday:
        emoji = TYPE_EMOJI.get(holiday["type"], "🔴")
        h_name = holiday["am"] if lang == "am" else holiday["en"]
        h_lbl = TYPE_LABEL[lang].get(holiday["type"], "በዓል")
        text += f"{emoji} <b>{h_lbl}:</b> {h_name}\n\n"

    # User reminders for this day
    day_rems = get_user_day_reminders(user_id, eth_year, eth_month, eth_day)
    if day_rems:
        if lang == "am":
            text += "🔔 <b>የእርስዎ ማስታወሻዎች:</b>\n"
        else:
            text += "🔔 <b>Your Reminders:</b>\n"
        for rem_id, msg, is_trig in day_rems:
            status = " (ተልኳል)" if is_trig and lang == "am" else " (Sent)" if is_trig else ""
            text += f"• <i>{html.escape(msg)}</i>{status}\n"
        text += "\n"
    else:
        if lang == "am":
            text += "<i>ለዚህ ቀን ምንም የተመዘገበ ማስታወሻ የለም።</i>\n\n"
        else:
            text += "<i>No reminders saved for this date.</i>\n\n"

    kb = []
    add_btn_text = "➕ ማስታወሻ ጨምር" if lang == "am" else "➕ Add Reminder"
    kb.append([InlineKeyboardButton(add_btn_text, callback_data=f"rem_add:{eth_year}:{eth_month}:{eth_day}")])

    if day_rems:
        for rem_id, msg, _ in day_rems:
            del_txt = f"🗑️ ሰርዝ: {msg[:15]}..." if lang == "am" else f"🗑️ Delete: {msg[:15]}..."
            kb.append([InlineKeyboardButton(del_txt, callback_data=f"rem_del:{rem_id}:{eth_year}:{eth_month}:{eth_day}")])

    back_txt = "⬅️ ወደ ቀን መቁጠሪያ" if lang == "am" else "⬅️ Back to Calendar"
    kb.append([InlineKeyboardButton(back_txt, callback_data=f"cal:{eth_year}:{eth_month}")])

    return text, InlineKeyboardMarkup(kb)


# ─── Telegram Handlers ────────────────────────────────────────────────────────

async def calendar_view_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main command handler for /view_calendar, /vcal, or menu button."""
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        track_activity(update, "/view_calendar")

        today_ed, today_em, today_ey = get_current_eth_date()
        text, kb = build_calendar_view(today_ey, today_em, uid, lang)

        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception as e:
        await send_error(update, context, e, "calendar_view_command")


async def calendar_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback query router for inline calendar interaction."""
    try:
        query = update.callback_query
        data = query.data
        uid = update.effective_user.id
        lang = get_lang(uid)
        track_activity(update)

        if data == "cal_ignore":
            await query.answer()
            return

        # ── Month selection menu ──
        if data.startswith("cal_months:"):
            eth_year = int(data.split(":")[1])
            m_text = f"📆 <b>ወር ምረጡ — {eth_year} ዓ.ም</b>" if lang == "am" else f"📆 <b>Select Month — {eth_year} E.C.</b>"
            months = ETH_MONTHS_AM if lang == "am" else ETH_MONTHS_EN
            
            keyboard = []
            row = []
            for i, name in enumerate(months, 1):
                row.append(InlineKeyboardButton(name, callback_data=f"cal:{eth_year}:{i}"))
                if len(row) == 3:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)

            tey, tem, _ = get_current_eth_date()
            t_label = "📍 ዛሬ" if lang == "am" else "📍 Today"
            keyboard.append([InlineKeyboardButton(t_label, callback_data=f"cal:{tey}:{tem}")])

            await query.edit_message_text(m_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            await query.answer()
            return

        # ── Calendar grid navigation ──
        if data.startswith("cal:"):
            parts = data.split(":")
            eth_year = int(parts[1])
            eth_month = int(parts[2])

            text, kb = build_calendar_view(eth_year, eth_month, uid, lang)
            try:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
            except Exception as edit_err:
                if "Message is not modified" not in str(edit_err):
                    raise edit_err
            await query.answer()
            return

        # ── Day click details ──
        if data.startswith("cal_day:"):
            parts = data.split(":")
            eth_year, eth_month, eth_day = int(parts[1]), int(parts[2]), int(parts[3])
            text, kb = build_day_detail_view(eth_year, eth_month, eth_day, uid, lang)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
            await query.answer()
            return

        # ── Add reminder prompt ──
        if data.startswith("rem_add:"):
            parts = data.split(":")
            eth_year, eth_month, eth_day = int(parts[1]), int(parts[2]), int(parts[3])
            
            context.user_data["awaiting_reminder"] = {
                "year": eth_year,
                "month": eth_month,
                "day": eth_day
            }

            m_name = ETH_MONTHS_AM[eth_month - 1] if lang == "am" else ETH_MONTHS_EN[eth_month - 1]
            if lang == "am":
                prompt = (
                    f"✍️ <b>ለ {m_name} {eth_day}፣ {eth_year} ዓ.ም ማስታወሻ ማስቀመጫ:</b>\n\n"
                    f"እባክዎ የማስታወሻ ጽሑፍዎን አሁን ይጻፉና ይላኩ (ምሳሌ፦ <i>የኪራይ ክፍያ/ስብሰባ</i>)፦"
                )
            else:
                prompt = (
                    f"✍️ <b>Add Reminder for {m_name} {eth_day}, {eth_year} E.C.:</b>\n\n"
                    f"Please type and send your reminder message below (e.g. <i>Pay rent / Team meeting</i>):"
                )

            cancel_txt = "❌ ሰርዝ" if lang == "am" else "❌ Cancel"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(cancel_txt, callback_data=f"cal_day:{eth_year}:{eth_month}:{eth_day}")]])
            await query.edit_message_text(prompt, parse_mode="HTML", reply_markup=kb)
            await query.answer()
            return

        # ── Delete reminder ──
        if data.startswith("rem_del:"):
            parts = data.split(":")
            rem_id = int(parts[1])
            eth_year, eth_month, eth_day = int(parts[2]), int(parts[3]), int(parts[4])
            delete_reminder(rem_id, uid)
            
            text, kb = build_day_detail_view(eth_year, eth_month, eth_day, uid, lang)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
            await query.answer(text="Deleted! / ተሰርዟል!" if lang == "am" else "Reminder deleted!")
            return

        # ── List all user reminders ──
        if data == "my_reminders":
            await show_my_reminders(query, context, uid, lang)
            return

        await query.answer()

    except Exception as e:
        await send_error(update, context, e, "calendar_view_callback")


async def handle_reminder_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Listens for text input when a user is in "awaiting_reminder" state.
    """
    if "awaiting_reminder" not in context.user_data:
        return False  # Not handled

    try:
        rem_info = context.user_data.pop("awaiting_reminder")
        eth_year = rem_info["year"]
        eth_month = rem_info["month"]
        eth_day = rem_info["day"]
        msg_text = update.message.text.strip()
        uid = update.effective_user.id
        lang = get_lang(uid)

        rem_id = add_reminder(uid, eth_year, eth_month, eth_day, msg_text)
        
        m_name = ETH_MONTHS_AM[eth_month - 1] if lang == "am" else ETH_MONTHS_EN[eth_month - 1]
        gd, gm, gy = eth_to_greg(eth_day, eth_month, eth_year)
        from .common import EN_MONTHS
        greg_str = f"{EN_MONTHS[gm-1]} {gd}, {gy}"

        if rem_id:
            if lang == "am":
                success_msg = (
                    f"✅ <b>ማስታወሻ ተመዝግቧል!</b>\n\n"
                    f"📅 ቀን፦ <b>{m_name} {eth_day}፣ {eth_year} ዓ.ም</b>\n"
                    f"📆 ፈረንጅ፦ <b>{greg_str}</b>\n\n"
                    f"📝 <b>ማስታወሻ፦</b> <i>{html.escape(msg_text)}</i>\n\n"
                    f"🔔 ቀኑ ሲደርስ ቦቱ በራሱ መልዕክት ይልክልዎታል።"
                )
            else:
                success_msg = (
                    f"✅ <b>Reminder Successfully Set!</b>\n\n"
                    f"📅 Date: <b>{m_name} {eth_day}, {eth_year} E.C.</b>\n"
                    f"📆 Gregorian: <b>{greg_str}</b>\n\n"
                    f"📝 <b>Note:</b> <i>{html.escape(msg_text)}</i>\n\n"
                    f"🔔 The bot will automatically notify you on this date!"
                )
        else:
            success_msg = "❌ Error saving reminder. Please try again."

        btn_txt = "📅 ወደ ቀን መቁጠሪያ" if lang == "am" else "📅 Back to Calendar"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(btn_txt, callback_data=f"cal_day:{eth_year}:{eth_month}:{eth_day}")]])
        await update.message.reply_text(success_msg, parse_mode="HTML", reply_markup=kb)
        return True
    except Exception as e:
        await send_error(update, context, e, "handle_reminder_text_input")
        return True


async def my_reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /reminders to list all active reminders."""
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        track_activity(update, "/reminders")
        rems = get_user_reminders(uid)

        m_name = ETH_MONTHS_AM if lang == "am" else ETH_MONTHS_EN

        if not rems:
            msg = "🔔 <b>ማስታወሻዎች</b>\n\n<i>ምንም የተመዘገበ ንቁ ማስታወሻ የለም።</i>" if lang == "am" else "🔔 <b>My Reminders</b>\n\n<i>You have no active reminders set.</i>"
            await update.message.reply_text(msg, parse_mode="HTML")
            return

        msg = f"🔔 <b>የተመዘገቡ ማስታወሻዎች ({len(rems)})</b>\n\n" if lang == "am" else f"🔔 <b>Your Active Reminders ({len(rems)})</b>\n\n"
        kb = []
        for r_id, y, m, d, g_date, text, is_trig, _ in rems:
            mn = m_name[m - 1]
            msg += f"• <b>{mn} {d}, {y}</b> ({g_date})\n  <i>{html.escape(text)}</i>\n\n"
            del_lbl = f"🗑️ ሰርዝ: {text[:15]}" if lang == "am" else f"🗑️ Del: {text[:15]}"
            kb.append([InlineKeyboardButton(del_lbl, callback_data=f"rem_del:{r_id}:{y}:{m}:{d}")])

        back_txt = "📅 ቀን መቁጠሪያ" if lang == "am" else "📅 Open Calendar"
        tey, tem, _ = get_current_eth_date()
        kb.append([InlineKeyboardButton(back_txt, callback_data=f"cal:{tey}:{tem}")])

        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await send_error(update, context, e, "my_reminders_command")


async def show_my_reminders(query, context, uid, lang):
    """Internal helper to render reminders for callback query."""
    rems = get_user_reminders(uid)
    m_name = ETH_MONTHS_AM if lang == "am" else ETH_MONTHS_EN

    if not rems:
        msg = "🔔 <b>ማስታወሻዎች</b>\n\n<i>ምንም የተመዘገበ ንቁ ማስታወሻ የለም።</i>" if lang == "am" else "🔔 <b>My Reminders</b>\n\n<i>You have no active reminders set.</i>"
        tey, tem, _ = get_current_eth_date()
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📅 ቀን መቁጠሪያ" if lang == "am" else "📅 Open Calendar", callback_data=f"cal:{tey}:{tem}")]])
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=kb)
        await query.answer()
        return

    msg = f"🔔 <b>የተመዘገቡ ማስታወሻዎች ({len(rems)})</b>\n\n" if lang == "am" else f"🔔 <b>Your Active Reminders ({len(rems)})</b>\n\n"
    kb = []
    for r_id, y, m, d, g_date, text, is_trig, _ in rems:
        mn = m_name[m - 1]
        msg += f"• <b>{mn} {d}, {y}</b> ({g_date})\n  <i>{html.escape(text)}</i>\n\n"
        del_lbl = f"🗑️ ሰርዝ: {text[:15]}" if lang == "am" else f"🗑️ Del: {text[:15]}"
        kb.append([InlineKeyboardButton(del_lbl, callback_data=f"rem_del:{r_id}:{y}:{m}:{d}")])

    back_txt = "📅 ቀን መቁጠሪያ" if lang == "am" else "📅 Open Calendar"
    tey, tem, _ = get_current_eth_date()
    kb.append([InlineKeyboardButton(back_txt, callback_data=f"cal:{tey}:{tem}")])

    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    await query.answer()
