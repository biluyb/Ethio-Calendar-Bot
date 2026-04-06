from datetime import date, timedelta

ETHIOPIAN_MONTHS = [
    "መስከረም","ጥቅምት","ኅዳር","ታኅሣሥ","ጥር","የካቲት",
    "መጋቢት","ሚያዝያ","ግንቦት","ሰኔ","ሐምሌ","ነሐሴ","ጳጉሜን"
]

EN_MONTHS = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

EN_DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
AM_DAYS = ["ሰኞ","ማክሰኞ","ረቡዕ","ሐሙስ","አርብ","ቅዳሜ","እሁድ"]


def parse_date(text):
    text = text.strip().replace("-", "/").replace(" ", "/")
    parts = text.split("/")
    if len(parts) != 3:
        return None
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except:
        return None


# 🔹 Ethiopian ➜ Gregorian
def eth_to_greg(d, m, y):
    new_year = date(y + 7, 9, 11)
    days = (m - 1) * 30 + (d - 1)
    g = new_year + timedelta(days=days)
    return g.day, g.month, g.year


# 🔹 Gregorian ➜ Ethiopian
def greg_to_eth(d, m, y):
    g = date(y, m, d)

    new_year = date(y, 9, 11)
    if g < new_year:
        new_year = date(y - 1, 9, 11)

    delta = (g - new_year).days
    eth_year = new_year.year - 7

    m = delta // 30 + 1
    d = delta % 30 + 1

    return d, m, eth_year


def format_greg(d, m, y):
    g = date(y, m, d)
    return f"{d}-{m}-{y} | {EN_DAYS[g.weekday()]}, {EN_MONTHS[m-1]}"


def format_eth(d, m, y):
    return f"{d}-{m}-{y} | {ETHIOPIAN_MONTHS[m-1]}"
