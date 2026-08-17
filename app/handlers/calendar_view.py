"""
Interactive Ethiopian & Gregorian Dual Calendar with Holiday Descriptions & Reminders
Provides:
- Dual Mode: Ethiopian Calendar (EC) & Gregorian Calendar (GC) with 1-click Mode Toggle
- 10-year navigation & 13-month / 12-month inline pickers
- Pixel-perfect 7-column Inline Keyboard grid
- Interactive day selection with rich Historical & Cultural Holiday Descriptions
- Integrated Date Reminder System (Add, View, Delete)
- Automated background notifications on due date
- Evangelist cycle & Gregorian/Ethiopian date alignment
- Full bilingual support (Amharic / English)
"""

import html
from calendar import monthrange
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.db import get_lang, get_eth_datetime
from app.db.reminder_db import add_reminder, get_user_reminders, get_user_day_reminders, get_month_user_reminder_days, delete_reminder
from app.utils import greg_to_eth, eth_to_greg, is_leap_eth
from app.holidays import get_month_holidays, get_day_type, TYPE_EMOJI, TYPE_LABEL
from .common import track_activity, send_error, check_blocked

# ─── Calendar Constants ───────────────────────────────────────────────────────

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

GREG_MONTHS_AM = [
    "ጃኑዋሪ (Jan)", "ፌብሩዋሪ (Feb)", "ማርች (Mar)", "ኤፕሪል (Apr)",
    "ሜይ (May)", "ጁን (Jun)", "ጁላይ (Jul)", "ኦገስት (Aug)",
    "ሴፕቴምበር (Sep)", "ኦክቶበር (Oct)", "ኖቬምበር (Nov)", "ዲሴምበር (Dec)"
]

GREG_MONTHS_EN = [
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December"
]

WEEKDAYS_AM = ["ሰኞ", "ማክ", "ረቡ", "ሐሙ", "አር", "ቅዳ", "እሁ"]
WEEKDAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def get_current_eth_date():
    """Returns today's Ethiopian date as (day, month, year)."""
    now = get_eth_datetime()
    return greg_to_eth(now.day, now.month, now.year)


def eth_days_in_month(eth_month: int, eth_year: int) -> int:
    """Returns number of days in an Ethiopian month."""
    if eth_month <= 12:
        return 30
    return 6 if is_leap_eth(eth_year) else 5


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


def render_eth_text_calendar(eth_year: int, eth_month: int, user_id: int, lang: str) -> str:
    """Generates a perfectly aligned monospace text grid for Ethiopian Calendar."""
    today_ed, today_em, today_ey = get_current_eth_date()
    holidays = get_month_holidays(eth_month, eth_year)
    user_rem_days = get_month_user_reminder_days(user_id, eth_year, eth_month)
    total_days = eth_days_in_month(eth_month, eth_year)
    
    gd1, gm1, gy1 = eth_to_greg(1, eth_month, eth_year)
    start_weekday = date(gy1, gm1, gd1).weekday()
    
    if lang == "am":
        header_line = "ሰኞ   ማክ   ረቡ   ሐሙ   አር   ቅዳ   እሁ"
    else:
        header_line = "Mon  Tue  Wed  Thu  Fri  Sat  Sun"
        
    lines = [f"<code>{header_line}</code>"]
    
    curr_week = ["   "] * start_weekday
    for d in range(1, total_days + 1):
        is_today = (d == today_ed and eth_month == today_em and eth_year == today_ey)
        has_rem = d in user_rem_days
        holiday = holidays.get(d)
        
        if is_today:
            cell = f"{d:2d}."
        elif has_rem:
            cell = f"{d:2d}*"
        elif holiday:
            cell = f"{d:2d}!"
        else:
            cell = f"{d:3d}"
            
        curr_week.append(cell)
        if len(curr_week) == 7:
            lines.append(f"<code>{'  '.join(curr_week)}</code>")
            curr_week = []
            
    if curr_week:
        curr_week += ["   "] * (7 - len(curr_week))
        lines.append(f"<code>{'  '.join(curr_week)}</code>")
        
    legend = "(. = ዛሬ | * = ማስታወሻ | ! = በዓል)" if lang == "am" else "(. = Today | * = Reminder | ! = Holiday)"
    lines.append(f"<code>{legend}</code>")
    return "\n".join(lines)


def render_greg_text_calendar(greg_year: int, greg_month: int, user_id: int, lang: str) -> str:
    """Generates a perfectly aligned monospace text grid for Gregorian Calendar."""
    now = get_eth_datetime()
    _, num_days = monthrange(greg_year, greg_month)
    start_weekday = date(greg_year, greg_month, 1).weekday()
    
    if lang == "am":
        header_line = "ሰኞ   ማክ   ረቡ   ሐሙ   አር   ቅዳ   እሁ"
    else:
        header_line = "Mon  Tue  Wed  Thu  Fri  Sat  Sun"
        
    lines = [f"<code>{header_line}</code>"]
    
    curr_week = ["   "] * start_weekday
    for d in range(1, num_days + 1):
        is_today = (d == now.day and greg_month == now.month and greg_year == now.year)
        ed, em, ey = greg_to_eth(d, greg_month, greg_year)
        
        hol = get_day_type(em, ed, ey)
        user_rems = get_user_day_reminders(user_id, ey, em, ed)
        has_rem = any(not r[2] for r in user_rems)
        
        if is_today:
            cell = f"{d:2d}."
        elif has_rem:
            cell = f"{d:2d}*"
        elif hol:
            cell = f"{d:2d}!"
        else:
            cell = f"{d:3d}"
            
        curr_week.append(cell)
        if len(curr_week) == 7:
            lines.append(f"<code>{'  '.join(curr_week)}</code>")
            curr_week = []
            
    if curr_week:
        curr_week += ["   "] * (7 - len(curr_week))
        lines.append(f"<code>{'  '.join(curr_week)}</code>")
        
    legend = "(. = ዛሬ | * = ማስታወሻ | ! = በዓል)" if lang == "am" else "(. = Today | * = Reminder | ! = Holiday)"
    lines.append(f"<code>{legend}</code>")
    return "\n".join(lines)


# ─── Ethiopian Calendar Builder ──────────────────────────────────────────────

def build_calendar_view(eth_year: int, eth_month: int, user_id: int, lang: str):
    """Builds Ethiopian Calendar message text and keyboard."""
    today_ed, today_em, today_ey = get_current_eth_date()
    month_name_am = ETH_MONTHS_AM[eth_month - 1]
    month_name_en = ETH_MONTHS_EN[eth_month - 1]
    evangelist = get_evangelist(eth_year)

    era_label_am = f"ዘመነ {evangelist['am']}" if evangelist else ""
    era_label_en = f"Year of {evangelist['en']}" if evangelist else ""

    if lang == "am":
        header = (
            f"🇪🇹 <b>የኢትዮጵያ ቀን መቁጠሪያ (EC)</b>\n"
            f"📅 <b>{month_name_am} {eth_year} ዓ.ም</b> ({era_label_am})\n"
        )
    else:
        header = (
            f"🇪🇹 <b>Ethiopian Calendar (EC)</b>\n"
            f"📅 <b>{month_name_en}, {eth_year} E.C.</b> ({era_label_en})\n"
        )

    # Gregorian equivalence range
    try:
        gd1, gm1, gy1 = eth_to_greg(1, eth_month, eth_year)
        total_days = eth_days_in_month(eth_month, eth_year)
        gd2, gm2, gy2 = eth_to_greg(total_days, eth_month, eth_year)
        
        m1 = GREG_MONTHS_EN[gm1-1][:3]
        m2 = GREG_MONTHS_EN[gm2-1][:3]
        greg_span = f"{m1} {gd1} - {m2} {gd2}, {gy1}" if gy1 == gy2 else f"{m1} {gd1}, {gy1} - {m2} {gd2}, {gy2}"
        if lang == "am":
            header += f"📆 <i>ፈረንጅ: {greg_span}</i>\n"
        else:
            header += f"📆 <i>GC Span: {greg_span}</i>\n"
    except Exception:
        pass

    header += "━━━━━━━━━━━━━━━━━\n"

    holidays = get_month_holidays(eth_month, eth_year)
    user_rem_days = get_month_user_reminder_days(user_id, eth_year, eth_month)

    legend = (
        "📍 = ዛሬ | 📌 = ዛሬ ከማስታወሻ ጋር | 🔴 = በዓል | 🔔 = ማስታወሻ\n<i>ቀን በመጫን ማስታወሻ እና የዕለቱን መግለጫ ይመልከቱ!</i>"
        if lang == "am" else
        "📍 = Today | 📌 = Today with Reminder | 🔴 = Holiday | 🔔 = Reminder\n<i>Click any date for details & holiday history!</i>"
    )

    event_list = ""
    if holidays:
        event_list += "\n📌 <b>የዚህ ወር በዓላት:</b>\n" if lang == "am" else "\n📌 <b>This Month's Events:</b>\n"
        for day, info in sorted(holidays.items()):
            emoji = TYPE_EMOJI.get(info["type"], "🔴")
            name = info["am"] if lang == "am" else info["en"]
            mname = month_name_am if lang == "am" else month_name_en
            event_list += f"{emoji} <b>{mname} {day}</b> — {name}\n"

    text_grid = render_eth_text_calendar(eth_year, eth_month, user_id, lang)
    full_text = f"{header}\n{text_grid}\n\n{legend}\n{event_list}"

    keyboard = []

    # 0. Mode Switcher Top Button
    switch_txt = "🔄 ወደ ፈረንጅ ቀን መቁጠሪያ (GC Mode)" if lang == "am" else "🔄 Switch to Gregorian Calendar (GC)"
    now = get_eth_datetime()
    keyboard.append([InlineKeyboardButton(switch_txt, callback_data=f"gcal:{now.year}:{now.month}")])

    # 1. Weekday Headers
    wd_row = WEEKDAYS_AM if lang == "am" else WEEKDAYS_EN
    keyboard.append([InlineKeyboardButton(d, callback_data="cal_ignore") for d in wd_row])

    # 2. Grid Days
    gd1, gm1, gy1 = eth_to_greg(1, eth_month, eth_year)
    start_weekday = date(gy1, gm1, gd1).weekday()

    curr_row = [InlineKeyboardButton("  ", callback_data="cal_ignore") for _ in range(start_weekday)]

    for d in range(1, total_days + 1):
        is_today = (d == today_ed and eth_month == today_em and eth_year == today_ey)
        has_rem = d in user_rem_days
        holiday = holidays.get(d)

        if is_today:
            label = f"📌{d:02d}" if has_rem else f"📍{d:02d}"
        elif has_rem:
            label = f"🔔{d:02d}"
        elif holiday:
            emoji = TYPE_EMOJI.get(holiday["type"], "🔴")
            label = f"{emoji}{d:02d}"
        else:
            label = f"{d:02d}"

        curr_row.append(InlineKeyboardButton(label, callback_data=f"cal_day:{eth_year}:{eth_month}:{d}"))

        if len(curr_row) == 7:
            keyboard.append(curr_row)
            curr_row = []

    if curr_row:
        while len(curr_row) < 7:
            curr_row.append(InlineKeyboardButton("  ", callback_data="cal_ignore"))
        keyboard.append(curr_row)

    # 3. Navigation Controls
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

    # 4. Quick Year Jumps
    year_row = []
    for delta in [-2, -1, 0, 1, 2]:
        yr = eth_year + delta
        if min_year <= yr <= max_year:
            btn_txt = f"•{yr}•" if yr == eth_year else str(yr)
            year_row.append(InlineKeyboardButton(btn_txt, callback_data=f"cal:{yr}:{eth_month}"))
    keyboard.append(year_row)

    # 5. Bottom Actions
    bottom_row = []
    if not (eth_year == today_ey and eth_month == today_em):
        t_txt = "📍 ዛሬ" if lang == "am" else "📍 Today"
        bottom_row.append(InlineKeyboardButton(t_txt, callback_data=f"cal:{today_ey}:{today_em}"))

    rem_txt = "🔔 ማስታወሻዎች" if lang == "am" else "🔔 Reminders"
    bottom_row.append(InlineKeyboardButton(rem_txt, callback_data="my_reminders"))
    keyboard.append(bottom_row)

    return full_text, InlineKeyboardMarkup(keyboard)


# ─── Gregorian Calendar Builder ──────────────────────────────────────────────

def build_greg_calendar_view(greg_year: int, greg_month: int, user_id: int, lang: str):
    """Builds professional Gregorian Calendar message text and 7-column grid keyboard."""
    now = get_eth_datetime()
    month_name_am = GREG_MONTHS_AM[greg_month - 1]
    month_name_en = GREG_MONTHS_EN[greg_month - 1]

    if lang == "am":
        header = (
            f"🌐 <b>የፈረንጅ ቀን መቁጠሪያ (GC)</b>\n"
            f"📅 <b>{month_name_am} {greg_year}</b>\n"
        )
    else:
        header = (
            f"🌐 <b>Gregorian Calendar (GC)</b>\n"
            f"📅 <b>{month_name_en} {greg_year}</b>\n"
        )

    # Ethiopian equivalence range for this Gregorian month
    try:
        _, num_days = monthrange(greg_year, greg_month)
        ed1, em1, ey1 = greg_to_eth(1, greg_month, greg_year)
        ed2, em2, ey2 = greg_to_eth(num_days, greg_month, greg_year)
        
        m1 = ETH_MONTHS_AM[em1-1] if lang == "am" else ETH_MONTHS_EN[em1-1]
        m2 = ETH_MONTHS_AM[em2-1] if lang == "am" else ETH_MONTHS_EN[em2-1]
        eth_span = f"{m1} {ed1} - {m2} {ed2}፣ {ey1}" if ey1 == ey2 else f"{m1} {ed1}፣ {ey1} - {m2} {ed2}፣ {ey2}"
        if lang == "am":
            header += f"🇪🇹 <i>የኢትዮጵያ፦ {eth_span}</i>\n"
        else:
            header += f"🇪🇹 <i>EC Equivalent: {eth_span}</i>\n"
    except Exception:
        num_days = 31

    header += "━━━━━━━━━━━━━━━━━\n"

    legend = (
        "📍 = ዛሬ | 📌 = ዛሬ ከማስታወሻ ጋር | 🔴 = በዓል | 🔔 = ማስታወሻ\n<i>ቀን በመጫን የኢትዮጵያ ቀኑን እና ማስታወሻን ይመልከቱ!</i>"
        if lang == "am" else
        "📍 = Today | 📌 = Today with Reminder | 🔴 = Holiday | 🔔 = Reminder\n<i>Click any date to see Ethiopian date & holiday history!</i>"
    )

    # Gather events occurring in this Gregorian month
    greg_events = []
    for gd in range(1, num_days + 1):
        ed, em, ey = greg_to_eth(gd, greg_month, greg_year)
        hol = get_day_type(em, ed, ey)
        if hol:
            greg_events.append((gd, ed, em, ey, hol))

    event_list = ""
    if greg_events:
        event_list += "\n📌 <b>የዚህ ወር በዓላት:</b>\n" if lang == "am" else "\n📌 <b>This Month's Events:</b>\n"
        for gd, ed, em, ey, info in greg_events:
            emoji = TYPE_EMOJI.get(info["type"], "🔴")
            hname = info["am"] if lang == "am" else info["en"]
            mname = ETH_MONTHS_AM[em-1] if lang == "am" else ETH_MONTHS_EN[em-1]
            event_list += f"{emoji} <b>{GREG_MONTHS_EN[greg_month-1][:3]} {gd}</b> ({mname} {ed}) — {hname}\n"

    text_grid = render_greg_text_calendar(greg_year, greg_month, user_id, lang)
    full_text = f"{header}\n{text_grid}\n\n{legend}\n{event_list}"

    keyboard = []

    # 0. Mode Switcher Top Button
    switch_txt = "🔄 ወደ ኢትዮጵያ ቀን መቁጠሪያ (EC Mode)" if lang == "am" else "🔄 Switch to Ethiopian Calendar (EC)"
    tey, tem, _ = get_current_eth_date()
    keyboard.append([InlineKeyboardButton(switch_txt, callback_data=f"cal:{tey}:{tem}")])

    # 1. Weekday Headers
    wd_row = WEEKDAYS_AM if lang == "am" else WEEKDAYS_EN
    keyboard.append([InlineKeyboardButton(d, callback_data="cal_ignore") for d in wd_row])

    # 2. Grid Days
    start_weekday = date(greg_year, greg_month, 1).weekday()
    curr_row = [InlineKeyboardButton("  ", callback_data="cal_ignore") for _ in range(start_weekday)]

    for d in range(1, num_days + 1):
        is_today = (d == now.day and greg_month == now.month and greg_year == now.year)
        ed, em, ey = greg_to_eth(d, greg_month, greg_year)
        
        hol = get_day_type(em, ed, ey)
        user_rems = get_user_day_reminders(user_id, ey, em, ed)
        # Check if there is any reminder that is NOT yet triggered
        has_rem = any(not r[2] for r in user_rems)

        if is_today:
            label = f"📌{d:02d}" if has_rem else f"📍{d:02d}"
        elif has_rem:
            label = f"🔔{d:02d}"
        elif hol:
            emoji = TYPE_EMOJI.get(hol["type"], "🔴")
            label = f"{emoji}{d:02d}"
        else:
            label = f"{d:02d}"

        curr_row.append(InlineKeyboardButton(label, callback_data=f"gcal_day:{greg_year}:{greg_month}:{d}"))

        if len(curr_row) == 7:
            keyboard.append(curr_row)
            curr_row = []

    if curr_row:
        while len(curr_row) < 7:
            curr_row.append(InlineKeyboardButton("  ", callback_data="cal_ignore"))
        keyboard.append(curr_row)

    # 3. Navigation Controls
    prev_month, prev_year = (greg_month - 1, greg_year) if greg_month > 1 else (12, greg_year - 1)
    next_month, next_year = (greg_month + 1, greg_year) if greg_month < 12 else (1, greg_year + 1)

    nav_row = [
        InlineKeyboardButton("⬅️ Prev", callback_data=f"gcal:{prev_year}:{prev_month}"),
        InlineKeyboardButton(f"📅 {GREG_MONTHS_EN[greg_month-1][:3]} {greg_year}", callback_data=f"gcal_months:{greg_year}"),
        InlineKeyboardButton("Next ➡️", callback_data=f"gcal:{next_year}:{next_month}")
    ]
    keyboard.append(nav_row)

    # 4. Quick Year Jumps
    year_row = []
    for delta in [-2, -1, 0, 1, 2]:
        yr = greg_year + delta
        btn_txt = f"•{yr}•" if yr == greg_year else str(yr)
        year_row.append(InlineKeyboardButton(btn_txt, callback_data=f"gcal:{yr}:{greg_month}"))
    keyboard.append(year_row)

    # 5. Bottom Actions
    bottom_row = []
    if not (greg_year == now.year and greg_month == now.month):
        t_txt = "📍 Today (GC)" if lang == "en" else "📍 ዛሬ (ፈረንጅ)"
        bottom_row.append(InlineKeyboardButton(t_txt, callback_data=f"gcal:{now.year}:{now.month}"))

    rem_txt = "🔔 ማስታወሻዎች" if lang == "am" else "🔔 Reminders"
    bottom_row.append(InlineKeyboardButton(rem_txt, callback_data="my_reminders"))
    keyboard.append(bottom_row)

    return full_text, InlineKeyboardMarkup(keyboard)


# ─── Day Details & Holiday Description View ──────────────────────────────────

def build_day_detail_view(eth_year: int, eth_month: int, eth_day: int, user_id: int, lang: str):
    """
    Builds day detail view with rich Holiday Historical & Cultural Descriptions.
    """
    m_am = ETH_MONTHS_AM[eth_month - 1]
    m_en = ETH_MONTHS_EN[eth_month - 1]
    
    gd, gm, gy = eth_to_greg(eth_day, eth_month, eth_year)
    from .common import EN_MONTHS
    greg_str = f"{EN_MONTHS[gm-1]} {gd}, {gy}"

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

    # Holiday check + Description
    holidays = get_month_holidays(eth_month, eth_year)
    holiday = holidays.get(eth_day)
    if holiday:
        emoji = TYPE_EMOJI.get(holiday["type"], "🔴")
        h_name = holiday["am"] if lang == "am" else holiday["en"]
        h_lbl = TYPE_LABEL[lang].get(holiday["type"], "በዓል")
        desc = holiday["desc_am"] if lang == "am" else holiday["desc_en"]

        text += f"{emoji} <b>{h_lbl}:</b> <b>{h_name}</b>\n"
        if desc:
            hdr = "📖 <b>ታሪክ እና ትርጉም (Description):</b>\n" if lang == "am" else "📖 <b>Holiday History & Significance:</b>\n"
            text += f"{hdr}<i>{desc}</i>\n"
        text += "\n"

    # User reminders
    day_rems = get_user_day_reminders(user_id, eth_year, eth_month, eth_day)
    if day_rems:
        text += "🔔 <b>የእርስዎ ማስታወሻዎች:</b>\n" if lang == "am" else "🔔 <b>Your Reminders:</b>\n"
        for rem_id, msg, is_trig in day_rems:
            status = " (ተልኳል)" if is_trig and lang == "am" else " (Sent)" if is_trig else ""
            text += f"• <i>{html.escape(msg)}</i>{status}\n"
        text += "\n"
    else:
        if not holiday:
            text += "<i>ለዚህ ቀን ምንም የተመዘገበ ማስታወሻ የለም።</i>\n\n" if lang == "am" else "<i>No reminders saved for this date.</i>\n\n"

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


# ─── Telegram Handlers & Callbacks ───────────────────────────────────────────

async def calendar_view_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main command handler for /view_calendar, /vcal, or menu button."""
    if await check_blocked(update): return
    try:
        uid = update.effective_user.id
        lang = get_lang(uid)
        track_activity(update, "/view_calendar")

        today_ed, today_em, today_ey = get_current_eth_date()
        text, kb = build_calendar_view(today_ey, today_em, uid, lang)

        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        await send_error(update, context, e, "calendar_view_command")


async def calendar_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback query router for dual inline calendar interaction."""
    if await check_blocked(update): return
    try:
        query = update.callback_query
        data = query.data
        uid = update.effective_user.id
        lang = get_lang(uid)
        track_activity(update)

        if data == "cal_ignore":
            await query.answer()
            return

        # ── Calendar Info Display ──
        if data == "show_calendar_info":
            from app.texts import INFO_AM, INFO_EN
            info_text = INFO_AM if lang == "am" else INFO_EN
            tey, tem, _ = get_current_eth_date()
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🗓 ቀን መቁጠሪያ ይክፈቱ (Open Calendar)" if lang == "am" else "🗓 Open Interactive Calendar", callback_data=f"cal:{tey}:{tem}")],
                [InlineKeyboardButton("📍 ዛሬ" if lang == "am" else "📍 Today", callback_data=f"cal:{tey}:{tem}")]
            ])
            await query.edit_message_text(info_text, parse_mode="HTML", reply_markup=kb)
            await query.answer()
            return

        # ── Ethiopian Month Selector Menu ──
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

        # ── Gregorian Month Selector Menu ──
        if data.startswith("gcal_months:"):
            greg_year = int(data.split(":")[1])
            m_text = f"🌐 <b>ወር ምረጡ — {greg_year} (GC)</b>" if lang == "am" else f"🌐 <b>Select Month — {greg_year} GC</b>"
            months = GREG_MONTHS_AM if lang == "am" else GREG_MONTHS_EN
            
            keyboard = []
            row = []
            for i, name in enumerate(months, 1):
                row.append(InlineKeyboardButton(name[:12], callback_data=f"gcal:{greg_year}:{i}"))
                if len(row) == 3:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)

            now = get_eth_datetime()
            t_label = "📍 ዛሬ (GC)" if lang == "am" else "📍 Today (GC)"
            keyboard.append([InlineKeyboardButton(t_label, callback_data=f"gcal:{now.year}:{now.month}")])

            await query.edit_message_text(m_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            await query.answer()
            return

        # ── Ethiopian Calendar Grid View ──
        if data.startswith("cal:"):
            parts = data.split(":")
            eth_year, eth_month = int(parts[1]), int(parts[2])
            text, kb = build_calendar_view(eth_year, eth_month, uid, lang)
            try:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
            except Exception as edit_err:
                if "Message is not modified" not in str(edit_err): raise edit_err
            await query.answer()
            return

        # ── Gregorian Calendar Grid View ──
        if data.startswith("gcal:"):
            parts = data.split(":")
            greg_year, greg_month = int(parts[1]), int(parts[2])
            text, kb = build_greg_calendar_view(greg_year, greg_month, uid, lang)
            try:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
            except Exception as edit_err:
                if "Message is not modified" not in str(edit_err): raise edit_err
            await query.answer()
            return

        # ── Ethiopian Day Click View ──
        if data.startswith("cal_day:"):
            parts = data.split(":")
            eth_year, eth_month, eth_day = int(parts[1]), int(parts[2]), int(parts[3])
            text, kb = build_day_detail_view(eth_year, eth_month, eth_day, uid, lang)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
            await query.answer()
            return

        # ── Gregorian Day Click View ──
        if data.startswith("gcal_day:"):
            parts = data.split(":")
            gy, gm, gd = int(parts[1]), int(parts[2]), int(parts[3])
            ey, em, ed = greg_to_eth(gd, gm, gy)
            text, kb = build_day_detail_view(ey, em, ed, uid, lang)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
            await query.answer()
            return

        # ── Add Reminder Prompt ──
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

        # ── Delete Reminder ──
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
    """Listens for text input when user is setting a reminder."""
    if "awaiting_reminder" not in context.user_data:
        return False

    try:
        rem_info = context.user_data.pop("awaiting_reminder")
        eth_year, eth_month, eth_day = rem_info["year"], rem_info["month"], rem_info["day"]
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
            success_msg = "❌ Error saving reminder."

        btn_txt = "📅 ወደ ቀን መቁጠሪያ" if lang == "am" else "📅 Back to Calendar"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(btn_txt, callback_data=f"cal_day:{eth_year}:{eth_month}:{eth_day}")]])
        await update.message.reply_text(success_msg, parse_mode="HTML", reply_markup=kb)
        return True
    except Exception as e:
        await send_error(update, context, e, "handle_reminder_text_input")
        return True


async def my_reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /reminders to list all active reminders."""
    if await check_blocked(update): return
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
