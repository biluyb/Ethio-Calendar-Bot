# Leap rules

def is_gregorian_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def is_ethiopian_leap(year):
    return (year + 1) % 4 == 0


# Julian Day

def gregorian_to_jd(year, month, day):
    a = (14 - month)//12
    y = year + 4800 - a
    m = month + 12*a - 3
    return day + ((153*m + 2)//5) + 365*y + y//4 - y//100 + y//400 - 32045


def jd_to_gregorian(jd):
    a = jd + 32044
    b = (4*a + 3)//146097
    c = a - (146097*b)//4
    d = (4*c + 3)//1461
    e = c - (1461*d)//4
    m = (5*e + 2)//153

    day = e - (153*m + 2)//5 + 1
    month = m + 3 - 12*(m//10)
    year = 100*b + d - 4800 + m//10

    return day, month, year


ETHIOPIAN_EPOCH = 1723856

def ethiopian_to_jd(year, month, day):
    return ETHIOPIAN_EPOCH + 365*(year-1) + (year-1)//4 + 30*(month-1) + day -1


def jd_to_ethiopian(jd):
    r = (jd - ETHIOPIAN_EPOCH) % 1461
    n = r % 365 + 365*(r//1460)
    year = 4*((jd - ETHIOPIAN_EPOCH)//1461) + r//365 - r//1460
    month = n//30 + 1
    day = n%30 + 1
    return day, month, year


def gregorian_to_ethiopian(d, m, y):
    return jd_to_ethiopian(gregorian_to_jd(y, m, d))


def ethiopian_to_gregorian(d, m, y):
    return jd_to_gregorian(ethiopian_to_jd(y, m, d))
