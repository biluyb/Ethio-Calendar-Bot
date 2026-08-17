"""
Ethiopian Public Holidays and Key Dates
Organized by Ethiopian month (1-13) and day within the month.
These are used to color-code the interactive calendar.
"""

# Format: {(eth_month, eth_day): {"en": "Name", "am": "ስም", "type": "holiday|closure|special"}}
# type: "holiday" = red (public holiday), "closure" = orange (office closed), "special" = green (special observance)

ETHIOPIAN_HOLIDAYS = {
    # ══ መስከረም / Meskerem ══
    (1, 1):  {"en": "Ethiopian New Year (Enkutatash)", "am": " እንቁጣጣሽ / አዲስ ዓመት", "type": "holiday"},
    (1, 11): {"en": "Finding of the True Cross (Meskel)", "am": "ደመራ (ምስቅ)", "type": "holiday"},
    (1, 17): {"en": "Meskel (True Cross)", "am": "መስቀል", "type": "holiday"},

    # ══ ጥቅምት / Tikimt ══
    # (typically no fixed holidays)

    # ══ ኅዳር / Hidar ══
    (3, 21): {"en": "Hidar Tsion (Celebration of Mary)", "am": "ሕዳር ጽዮን", "type": "special"},

    # ══ ታኅሣሥ / Tahsas ══
    (4, 29): {"en": "Christmas Eve (Gena / Lidat)", "am": "ሊደት ዋዜማ / ጋና", "type": "closure"},
    (4, 29): {"en": "Ethiopian Christmas Eve", "am": "ጋና ዋዜማ", "type": "closure"},

    # ══ ጥር / Tir ══
    (5, 1):  {"en": "Ethiopian Christmas (Gena / Lidat)", "am": "ጋና / ልደት", "type": "holiday"},
    (5, 11): {"en": "Ethiopian Epiphany (Timkat)", "am": "ጥምቀት", "type": "holiday"},
    (5, 12): {"en": "Ethiopian Epiphany 2nd Day", "am": "ጥምቀት (2ኛ ቀን)", "type": "holiday"},

    # ══ የካቲት / Yekatit ══
    (6, 23): {"en": "Victory of Adwa Day", "am": "የዓድዋ ድል ቀን", "type": "holiday"},

    # ══ መጋቢት / Megabit ══
    # (Easter is moveable – handled separately)

    # ══ ሚያዝያ / Miyazia ══
    (8, 23): {"en": "Martyrs' Day", "am": "የሰማዕታት ቀን", "type": "holiday"},
    (8, 27): {"en": "Patriots' Victory Day (Ethiopian Patriots Day)", "am": "የፋሺስት ሽንፈት ቀን", "type": "holiday"},

    # ══ ግንቦት / Ginbot ══
    (9, 20): {"en": "Downfall of Derg Regime", "am": "ደርግ የወደቀበት ቀን", "type": "holiday"},

    # ══ ሰኔ / Sene ══
    # (typically no fixed national holidays)

    # ══ ሐምሌ / Hamle ══
    # (typically no fixed national holidays)

    # ══ ነሐሴ / Nehase ══
    # (typically no fixed national holidays)

    # ══ ጳጉሜ / Pagume ══
    (13, 1): {"en": "Pagume (13th Month Start)", "am": "ጳጉሜ ይጀምራል", "type": "special"},
    (13, 5): {"en": "Pagume End (non-leap year)", "am": "ጳጉሜ ቀን (ዓ.ም)", "type": "special"},
    (13, 6): {"en": "Pagume End (leap year)", "am": "ጳጉሜ ቀን (ዘመነ ሉቃስ)", "type": "special"},
}

# Islamic holidays are approximate (lunar-based, shift each year)
# These are rough fixed approximations commonly observed in Ethiopia
ISLAMIC_OBSERVANCES = {
    # Eid al-Fitr and Eid al-Adha vary yearly; handled by annotation only
}

def get_day_type(eth_month: int, eth_day: int) -> dict | None:
    """Returns the holiday info dict for a given Ethiopian date, or None."""
    return ETHIOPIAN_HOLIDAYS.get((eth_month, eth_day))


def get_month_holidays(eth_month: int) -> dict:
    """Returns all holidays for an Ethiopian month as {day: info_dict}."""
    return {
        day: info
        for (m, day), info in ETHIOPIAN_HOLIDAYS.items()
        if m == eth_month
    }


# Color/emoji mapping by type
TYPE_EMOJI = {
    "holiday": "🔴",  # Red: Public holiday (offices closed)
    "closure": "🟠",  # Orange: Early closure or half-day
    "special": "🟢",  # Green: Special observance / celebration
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
