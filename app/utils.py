"""
Date Conversion Utilities for the Ethiopian Calendar.
Provides algorithms for converting between Ethiopian (EC) and Gregorian (GC) calendars,
as well as date validation and parsing logic.
"""

from datetime import date, timedelta, datetime
import calendar

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
    """
    Attempts to parse a date string in various formats (DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY).
    Returns a tuple (day, month, year) or None if parsing fails.
    """
    if not text or not isinstance(text, str):
        return None
        
    # Standardize delimiters
    normalized = text.strip().replace("-", "/").replace(" ", "/").replace(".", "/")
    parts = normalized.split("/")
    
    if len(parts) != 3:
        return None
        
    try:
        d, m, y = map(int, parts)
        # Basic sanity check
        if y < 1 or m < 1 or d < 1:
            return None
        return d, m, y
    except (ValueError, TypeError):
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
        # Determine Gregorian New Year for the given Ethiopian year
        # Ethiopian leap year is y % 4 == 3. 
        # The GC New Year shift to Sept 12 happens when the PREVIOUS EC year was leap.
        # So if (y-1) % 4 == 3, New Year is Sept 12.
        if (y - 1) % 4 == 3:
            gw = date(y + 7, 9, 12)
        else:
            gw = date(y + 7, 9, 11)
            
        days = (m - 1) * 30 + (d - 1)
        g = gw + timedelta(days=days)
        return g.day, g.month, g.year
    except OverflowError:
        raise ValueError("Date out of range")


# 🔹 Gregorian ➜ Ethiopian
def greg_to_eth(d, m, y):
    try:
        g = date(y, m, d)
        
        # New Year in GC for EC (y-7)
        # We need to know if (y-8) EC was leap to decide if New Year is Sept 11 or 12.
        ec_year_approx = y - 8
        if ec_year_approx % 4 == 3: # Previous EC year (y-8) was leap
            new_year = date(y, 9, 12)
        else:
            new_year = date(y, 9, 11)

        if g < new_year:
            # We are in the previous EC year
            # Check if (y-9) EC was leap
            if (y - 9) % 4 == 3:
                new_year = date(y - 1, 9, 12)
            else:
                new_year = date(y - 1, 9, 11)
                
        delta = (g - new_year).days
        eth_year = new_year.year - 7
        
        # Adjust for the Sept 12 case in the mapping
        # If new_year.day was 12, then eth_year is indeed new_year.year - 7
        # e.g. Sept 12, 2023 -> Meskerem 1, 2016. 2023 - 7 = 2016. Correct.

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

def calculate_age(birth_date, current_date):
    """Calculates age in years, months, and days."""
    years = current_date.year - birth_date.year
    months = current_date.month - birth_date.month
    days = current_date.day - birth_date.day
    
    if days < 0:
        months -= 1
        # Get days in the previous month
        prev_month = (current_date.month - 2) % 12 + 1
        prev_year = current_date.year if current_date.month > 1 else current_date.year - 1
        _, days_in_prev = calendar.monthrange(prev_year, prev_month)
        days += days_in_prev
        
    if months < 0:
        years -= 1
        months += 12
        
    return years, months, days
