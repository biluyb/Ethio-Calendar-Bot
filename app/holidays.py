"""
Ethiopian Public Holidays and Key Dates Database
Supports fixed Ethiopian holidays, fixed Gregorian holidays (e.g. May Day),
and moveable Christian/Islamic holidays for 10+ years.
"""

from app.utils import eth_to_greg, greg_to_eth

# Fixed Ethiopian Holidays: (eth_month, eth_day) -> info dict
FIXED_ETHIOPIAN_HOLIDAYS = {
    # ══ መስከረም / Meskerem ══
    (1, 1):   {"en": "Ethiopian New Year (Enkutatash)", "am": "አዲስ ዓመት (እንቁጣጣሽ)", "type": "holiday"},
    (1, 16):  {"en": "Demera (Cross Eve)", "am": "ደመራ (መስቀል ዋዜማ)", "type": "special"},
    (1, 17):  {"en": "Finding of the True Cross (Meskel)", "am": "መስቀል", "type": "holiday"},

    # ══ ኅዳር / Hidar ══
    (3, 20):  {"en": "Ethiopian National Unity Day", "am": "የብሔር ብሔረሰቦች ቀን", "type": "holiday"},
    (3, 21):  {"en": "Hidar Tsion (Celebration of Mary)", "am": "ሕዳር ጽዮን", "type": "special"},

    # ══ ታኅሣሥ / Tahsas ══
    (4, 28):  {"en": "Ethiopian Christmas Eve (Leap Year)", "am": "የገና ዋዜማ (ዘመነ ሉቃስ)", "type": "closure"},
    (4, 29):  {"en": "Ethiopian Christmas / Gena", "am": "ገና / ልደት", "type": "holiday"},

    # ══ ጥር / Tir ══
    (5, 1):   {"en": "Ethiopian Christmas Day (Tir 1)", "am": "ልደት (ጥር 1)", "type": "holiday"},
    (5, 11):  {"en": "Ethiopian Epiphany (Timkat)", "am": "ጥምቀት", "type": "holiday"},
    (5, 12):  {"en": "Epiphany 2nd Day (Kana ZeGalila)", "am": "ቃና ዘገሊላ (ጥምቀት 2ኛ ቀን)", "type": "special"},

    # ══ የካቲት / Yekatit ══
    (6, 12):  {"en": "Ethiopian Martyrs' Day (Yekatit 12)", "am": "የሰማዕታት ቀን (የካቲት 12)", "type": "holiday"},
    (6, 23):  {"en": "Victory of Adwa Day", "am": "የዓድዋ ድል በዓል", "type": "holiday"},

    # ══ ሚያዝያ / Miyazia ══
    (8, 27):  {"en": "Patriots' Victory Day", "am": "የአርበኞች (የድል) ቀን", "type": "holiday"},

    # ══ ግንቦት / Ginbot ══
    (9, 20):  {"en": "Downfall of Derg Regime", "am": "የደርግ የወደቀበት ቀን (ግንቦት 20)", "type": "holiday"},

    # ══ ጳጉሜ / Pagume ══
    (13, 1):  {"en": "Pagume Start", "am": "ጳጉሜ ይጀምራል", "type": "special"},
    (13, 5):  {"en": "Pagume 5 (End of Year)", "am": "ጳጉሜ 5", "type": "special"},
    (13, 6):  {"en": "Pagume 6 (Leap Year)", "am": "ጳጉሜ 6 (ዘመነ ሉቃስ)", "type": "special"},
}


# Moveable holidays mapped by (eth_year, eth_month, eth_day)
MOVEABLE_HOLIDAYS = {
    # ── 2015 EC (2022/2023 GC) ──
    (2015, 1, 16):  {"en": "Mawlid", "am": "መውሊድ", "type": "holiday"},
    (2015, 8, 6):   {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday"},
    (2015, 8, 8):   {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday"},
    (2015, 8, 13):  {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday"},
    (2015, 10, 21): {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday"},

    # ── 2016 EC (2023/2024 GC) ──
    (2016, 1, 16):  {"en": "Mawlid", "am": "መውሊድ", "type": "holiday"},
    (2016, 8, 2):   {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday"},
    (2016, 8, 25):  {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday"},
    (2016, 8, 27):  {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday"},
    (2016, 10, 9):  {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday"},

    # ── 2017 EC (2024/2025 GC) ──
    (2017, 1, 5):   {"en": "Mawlid", "am": "መውሊድ", "type": "holiday"},
    (2017, 7, 21):  {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday"},
    (2017, 8, 10):  {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday"},
    (2017, 8, 12):  {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday"},
    (2017, 9, 29):  {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday"},
    (2017, 12, 29): {"en": "Mawlid", "am": "መውሊድ", "type": "holiday"},

    # ── 2018 EC (2025/2026 GC) ──
    (2018, 7, 11):  {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday"},
    (2018, 8, 2):   {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday"},
    (2018, 8, 4):   {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday"},
    (2018, 9, 19):  {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday"},
    (2018, 12, 20): {"en": "Mawlid", "am": "መውሊድ", "type": "holiday"},

    # ── 2019 EC (2026/2027 GC) ──
    (2019, 6, 30):  {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday"},
    (2019, 8, 22):  {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday"},
    (2019, 8, 24):  {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday"},
    (2019, 9, 9):   {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday"},
    (2019, 12, 9):  {"en": "Mawlid", "am": "መውሊድ", "type": "holiday"},

    # ── 2020 EC (2027/2028 GC) ──
    (2020, 6, 18):  {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday"},
    (2020, 8, 6):   {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday"},
    (2020, 8, 8):   {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday"},
    (2020, 8, 27):  {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday"},
    (2020, 11, 27): {"en": "Mawlid", "am": "መውሊድ", "type": "holiday"},

    # ── 2021 EC (2028/2029 GC) ──
    (2021, 6, 8):   {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday"},
    (2021, 7, 28):  {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday"},
    (2021, 7, 30):  {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday"},
    (2021, 8, 16):  {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday"},
    (2021, 11, 17): {"en": "Mawlid", "am": "መውሊድ", "type": "holiday"},

    # ── 2022 EC (2029/2030 GC) ──
    (2022, 5, 27):  {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday"},
    (2022, 8, 5):   {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday"},
    (2022, 8, 18):  {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday"},
    (2022, 8, 20):  {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday"},
    (2022, 11, 6):  {"en": "Mawlid", "am": "መውሊድ", "type": "holiday"},

    # ── 2023 EC (2030/2031 GC) ──
    (2023, 5, 16):  {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday"},
    (2023, 7, 25):  {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday"},
    (2023, 8, 3):   {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday"},
    (2023, 8, 5):   {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday"},
    (2023, 10, 26): {"en": "Mawlid", "am": "መውሊድ", "type": "holiday"},

    # ── 2024 EC (2031/2032 GC) ──
    (2024, 5, 5):   {"en": "Eid al-Fitr", "am": "ዒድ አል ፊጥር", "type": "holiday"},
    (2024, 7, 14):  {"en": "Eid al-Adha", "am": "ዒድ አል አድሃ", "type": "holiday"},
    (2024, 8, 22):  {"en": "Ethiopian Good Friday (Siklet)", "am": "ስቅለት", "type": "holiday"},
    (2024, 8, 24):  {"en": "Ethiopian Easter (Fasika)", "am": "ፋሲካ", "type": "holiday"},
    (2024, 10, 15): {"en": "Mawlid", "am": "መውሊድ", "type": "holiday"},
}


def get_month_holidays(eth_month: int, eth_year: int = None) -> dict:
    """
    Returns all holidays for an Ethiopian month as {day: info_dict}.
    Includes:
    1. Fixed Ethiopian holidays
    2. Fixed Gregorian holidays (International Workers' Day May 1 GC)
    3. Moveable Christian & Islamic holidays for the given year
    """
    holidays = {}

    # 1. Fixed Ethiopian Holidays
    for (m, d), info in FIXED_ETHIOPIAN_HOLIDAYS.items():
        if m == eth_month:
            holidays[d] = info

    # 2. Fixed Gregorian Holiday: May 1 (Workers' Day)
    if eth_year:
        try:
            gd1, gm1, gy1 = eth_to_greg(1, eth_month, eth_year)
            w_d, w_m, w_y = greg_to_eth(1, 5, gy1)
            if w_m == eth_month:
                holidays[w_d] = {
                    "en": "International Workers' Day",
                    "am": "የዓለም ሠራተኞች (የላብ አደሮች) ቀን",
                    "type": "holiday"
                }
        except Exception:
            pass

    # 3. Moveable Holidays
    if eth_year:
        for (y, m, d), info in MOVEABLE_HOLIDAYS.items():
            if y == eth_year and m == eth_month:
                holidays[d] = info

    return holidays


def get_day_type(eth_month: int, eth_day: int, eth_year: int = None) -> dict | None:
    """Returns holiday info dict for a specific Ethiopian date, or None."""
    month_hols = get_month_holidays(eth_month, eth_year)
    return month_hols.get(eth_day)


# Emoji mapping by holiday type
TYPE_EMOJI = {
    "holiday": "🔴",  # Public Holiday (Offices closed)
    "closure": "🟠",  # Early closure or half-day
    "special": "🟢",  # Special religious / national observance
}

TYPE_LABEL = {
    "en": {
        "holiday": "Public Holiday",
        "closure": "Office Closure",
        "special": "Special Observance",
    },
    "am": {
        "holiday": "የህዝብ በዓል",
        "closure": "ቢሮ ዝጋ",
        "special": "ልዩ ቀን",
    }
}
