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


def is_leap_eth(year):
    """Ethiopian leap year rule: (year + 1) % 4 == 0"""
    return (year + 1) % 4 == 0


def is_valid_eth_date(d, m, y):
    """Validates Ethiopian date values and year range."""
    if not (1 <= y <= 9991): # Stay within Python date range when converting (+8)
        return False, "Year out of range (1-9991)"
    
    if not (1 <= m <= 13):
        return False, "Month must be between 1 and 13"
    
    if 1 <= m <= 12:
        if not (1 <= d <= 30):
            return False, f"Month {m} must have 1-30 days"
    else: # m == 13 (Pagume)
        limit = 6 if is_leap_eth(y) else 5
        if not (1 <= d <= limit):
            return False, f"Pagume in {y} must have 1-{limit} days"
            
    return True, "Valid"


# 🔹 Ethiopian ➜ Gregorian
def eth_to_greg(d, m, y):
    is_valid, error_msg = is_valid_eth_date(d, m, y)
    if not is_valid:
        raise ValueError(error_msg)
        
    try:
        new_year = date(y + 7, 9, 11)
        days = (m - 1) * 30 + (d - 1)
        g = new_year + timedelta(days=days)
        return g.day, g.month, g.year
    except OverflowError:
        raise ValueError("Date out of range")


# 🔹 Gregorian ➜ Ethiopian
def greg_to_eth(d, m, y):
    try:
        g = date(y, m, d)

        new_year = date(y, 9, 11)
        if g < new_year:
            if y <= 1:
                raise ValueError("Year out of range")
            new_year = date(y - 1, 9, 11)

        delta = (g - new_year).days
        eth_year = new_year.year - 7

        m_eth = delta // 30 + 1
        d_eth = delta % 30 + 1

        return d_eth, m_eth, eth_year
    except (ValueError, OverflowError) as e:
        raise ValueError(str(e))


def format_greg(d, m, y):
    g = date(y, m, d)
    return f"{d}-{m}-{y} | {EN_DAYS[g.weekday()]}, {EN_MONTHS[m-1]}"


def format_eth(d, m, y):
    return f"{d}-{m}-{y} | {ETHIOPIAN_MONTHS[m-1]}"
