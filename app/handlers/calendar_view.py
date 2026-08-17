"""
Interactive Ethiopian Calendar Handler
Provides a stunning month-view calendar with:
- 10-year navigation (current year ± 5 years into future)
- Ethiopian public holidays shown with colored emoji badges
- Gregorian date equivalents shown
- Full bilingual support (Amharic / English)
- Today highlighted
- Month navigation with inline buttons
"""

from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.db import get_lang
from app.utils import greg_to_eth, eth_to_greg, is_leap_eth
from app.holidays import get_month_holidays, TYPE_EMOJI, TYPE_LABEL
from .common import track_activity, send_error

# ─── Ethiopian Calendar Constants ────────────────────────────────────────────

ETH_MONTHS_AM = [
    "መስከረም", "ጥቅምት", "ኅዳር", "ታኅሣሥ",
    "ጥር", "የካቲት", "መጋቢት", "ሚያዝያ",
    "ግንቦት", "ሰኔ", "ሐምሌ ", "ነሐሴ", "ጳጉሜ"
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
    # Pagume (month 13)
    return 6 if is_leap_eth(eth_year) else 5


def get_weekday_of_eth_day1(eth_month: int, eth_year: int) -> int:
    """Returns Python weekday (Mon=0, Sun=6) of day 1 of a given Ethiopian month."""
    gd, gm, gy = eth_to_greg(1, eth_month, eth_year)
    return date(gy, gm, gd).weekday()


def build_calendar_text(eth_year: int, eth_month: int, lang: str) -> str:
    """
    Builds a beautiful text-based monthly calendar for Telegram.
    Highlights: today, holidays, and shows Gregorian date for day 1.
    Returns the formatted text.
    """
    today_ed, today_em, today_ey = get_current_eth_date()

    month_name_am = ETH_MONTHS_AM[eth_month - 1]
    month_name_en = ETH_MONTHS_EN[eth_month - 1]
    evangelist = get_evangelist(eth_year)
    
    # Month header
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

    # Gregorian equivalent for day 1
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

    # Weekday row
    wd_row = WEEKDAYS_AM if lang == "am" else WEEKDAYS_EN
    header += "  ".join(f"<code>{d}</code>" for d in wd_row) + "\n"

    # Get holidays for this month
    holidays = get_month_holidays(eth_month, eth_year)
    total_days = eth_days_in_month(eth_month, eth_year)
    start_weekday = get_weekday_of_eth_day1(eth_month, eth_year)

    # Build calendar grid as lines
    calendar_lines = []
    week = ["  "] * start_weekday  # Leading blanks

    for day in range(1, total_days + 1):
        is_today = (day == today_ed and eth_month == today_em and eth_year == today_ey)
        holiday = holidays.get(day)

        if is_today:
            cell = f"[{day:2d}]"  # Today in brackets
        elif holiday:
            emoji = TYPE_EMOJI.get(holiday["type"], "⚪")
            cell = f"{emoji}{day:2d}"
        else:
            cell = f"  {day:2d}"

        week.append(cell)
        if len(week) == 7:
            calendar_lines.append("  ".join(week))
            week = []

    if week:  # Remaining days
        week += ["  "] * (7 - len(week))
        calendar_lines.append("  ".join(week))

    calendar_str = "\n".join(f"<code>{line}</code>" for line in calendar_lines)

    # Legend
    legend_parts = []
    if any(h["type"] == "holiday" for h in holidays.values()):
        legend_parts.append(f"🔴 {TYPE_LABEL[lang]['holiday']}")
    if any(h["type"] == "closure" for h in holidays.values()):
        legend_parts.append(f"🟠 {TYPE_LABEL[lang]['closure']}")
    if any(h["type"] == "special" for h in holidays.values()):
        legend_parts.append(f"🟢 {TYPE_LABEL[lang]['special']}")

    today_label = "[ ] = ዛሬ" if lang == "am" else "[ ] = Today"
    legend_parts.append(today_label)
    legend = "\n".join(legend_parts)

    # Holidays list
    holiday_list = ""
    if holidays:
        if lang == "am":
            holiday_list = "\n\n📌 <b>የዚህ ወር በዓላት:</b>\n"
        else:
            holiday_list = "\n\n📌 <b>This Month's Events:</b>\n"
        for day, info in sorted(holidays.items()):
            emoji = TYPE_EMOJI.get(info["type"], "⚪")
            name = info["am"] if lang == "am" else info["en"]
            holiday_list += f"{emoji} <b>{month_name_am if lang == 'am' else month_name_en} {day}</b> — {name}\n"

    return f"{header}\n{calendar_str}\n\n{legend}{holiday_list}"


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


def build_nav_keyboard(eth_year: int, eth_month: int, lang: str) -> InlineKeyboardMarkup:
    """Builds the navigation keyboard for the calendar."""
    # Valid year range: current EC year - 1 to current EC year + 10
    today_ed, today_em, today_ey = get_current_eth_date()
    min_year = today_ey - 1
    max_year = today_ey + 10

    # Previous / Next month
    prev_month, prev_year = (eth_month - 1, eth_year) if eth_month > 1 else (13, eth_year - 1)
    next_month, next_year = (eth_month + 1, eth_year) if eth_month < 13 else (1, eth_year + 1)

    can_prev = prev_year >= min_year
    can_next = next_year <= max_year

    row1 = []
    if can_prev:
        row1.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"cal:{prev_year}:{prev_month}"))
    
    month_name = ETH_MONTHS_AM[eth_month - 1] if lang == "am" else ETH_MONTHS_EN[eth_month - 1]
    row1.append(InlineKeyboardButton(f"📅 {month_name} {eth_year}", callback_data="cal_ignore"))
    
    if can_next:
        row1.append(InlineKeyboardButton("Next ➡️", callback_data=f"cal:{next_year}:{next_month}"))

    # Year jump row
    row2 = []
    for delta in [-2, -1, 0, 1, 2]:
        yr = eth_year + delta
        if min_year <= yr <= max_year:
            label = f"·{yr}·" if yr == eth_year else str(yr)
            row2.append(InlineKeyboardButton(label, callback_data=f"cal:{yr}:{eth_month}"))

    # Quick jump to today
    row3 = []
    if not (eth_year == today_ey and eth_month == today_em):
        today_label = "📍 ዛሬ" if lang == "am" else "📍 Today"
        row3.append(InlineKeyboardButton(today_label, callback_data=f"cal:{today_ey}:{today_em}"))

    # Month selector for current year
    month_label = "📆 ወር ምረጥ" if lang == "am" else "📆 Pick Month"
    row3.append(InlineKeyboardButton(month_label, callback_data=f"cal_months:{eth_year}"))

    keyboard = [row1, row2, row3] if row3 else [row1, row2]
    return InlineKeyboardMarkup(keyboard)


def build_month_picker_keyboard(eth_year: int, lang: str) -> InlineKeyboardMarkup:
    """Builds a 3-column month picker keyboard."""
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

    # Today's month
    ted, tem, tey = get_current_eth_date()
    today_label = "📍 ዛሬ" if lang == "am" else "📍 Back to Today"
    keyboard.append([InlineKeyboardButton(today_label, callback_data=f"cal:{tey}:{tem}")])

    return InlineKeyboardMarkup(keyboard)


# ─── Telegram Handlers ────────────────────────────────────────────────────────

async def calendar_view_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main entry: /view_calendar or menu button.
    Shows the current Ethiopian month calendar.
    """
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        track_activity(update, "/view_calendar")

        today_ed, today_em, today_ey = get_current_eth_date()

        text = build_calendar_text(today_ey, today_em, lang)
        kb = build_nav_keyboard(today_ey, today_em, lang)

        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception as e:
        await send_error(update, context, e, "calendar_view_command")


async def calendar_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles cal:{year}:{month} and cal_months:{year} callbacks.
    """
    try:
        query = update.callback_query
        data = query.data
        uid = update.effective_user.id
        lang = get_lang(uid)
        track_activity(update)

        if data == "cal_ignore":
            await query.answer()
            return

        if data.startswith("cal_months:"):
            eth_year = int(data.split(":")[1])
            if lang == "am":
                month_text = f"📆 <b>ወር ምረጡ — {eth_year} ዓ.ም</b>"
            else:
                month_text = f"📆 <b>Select Month — {eth_year} E.C.</b>"
            kb = build_month_picker_keyboard(eth_year, lang)
            await query.edit_message_text(month_text, parse_mode="HTML", reply_markup=kb)
            await query.answer()
            return

        if data.startswith("cal:"):
            parts = data.split(":")
            eth_year = int(parts[1])
            eth_month = int(parts[2])

            text = build_calendar_text(eth_year, eth_month, lang)
            kb = build_nav_keyboard(eth_year, eth_month, lang)

            try:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
            except Exception as edit_err:
                if "Message is not modified" not in str(edit_err):
                    raise edit_err
            await query.answer()
            return

        await query.answer()

    except Exception as e:
        await send_error(update, context, e, "calendar_view_callback")
