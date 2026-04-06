from datetime import date, timedelta

# Ethiopian calendar epoch reference (Meskerem 1, Year 1)
ETHIOPIAN_EPOCH = date(8, 8, 29)

def is_gregorian_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def is_ethiopian_leap(year):
    return (year + 1) % 4 == 0

def gregorian_to_ethiopian(day, month, year):
    g_date = date(year, month, day)
    delta_days = (g_date - ETHIOPIAN_EPOCH).days

    eth_year = delta_days // 365
    remaining = delta_days % 365

    leap_days = eth_year // 4
    remaining -= leap_days

    while remaining < 0:
        eth_year -= 1
        remaining += 365
        if is_ethiopian_leap(eth_year):
            remaining += 1

    eth_month = remaining // 30 + 1
    eth_day = remaining % 30 + 1

    return eth_day, eth_month, eth_year

def ethiopian_to_gregorian(day, month, year):
    days = (year * 365) + (year // 4)
    days += (month - 1) * 30
    days += (day - 1)

    g_date = ETHIOPIAN_EPOCH + timedelta(days=days)
    return g_date.day, g_date.month, g_date.year
