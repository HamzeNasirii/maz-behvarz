def gregorian_to_jalali(g_year, g_month, g_day):
    """
    تبدیل ساده‌ی میلادی به شمسی (بدون کتابخونه‌ی خارجی) — فقط برای
    نمایش تاریخ روی نامه‌ها استفاده می‌شود.
    """
    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    j_days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]

    gy = g_year - 1600
    gm = g_month - 1
    gd = g_day - 1

    g_day_no = 365 * gy + (gy + 3) // 4 - (gy + 99) // 100 + (gy + 399) // 400
    for i in range(gm):
        g_day_no += g_days_in_month[i]
    if gm > 1 and ((g_year % 4 == 0 and g_year % 100 != 0) or (g_year % 400 == 0)):
        g_day_no += 1
    g_day_no += gd

    j_day_no = g_day_no - 79

    j_np = j_day_no // 12053
    j_day_no %= 12053

    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461

    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365

    for i in range(11):
        if j_day_no < j_days_in_month[i]:
            jm = i + 1
            jd = j_day_no + 1
            break
        j_day_no -= j_days_in_month[i]
    else:
        jm = 12
        jd = j_day_no + 1

    return jy, jm, jd


def format_jalali_today():
    from django.utils import timezone

    today = timezone.localdate()
    jy, jm, jd = gregorian_to_jalali(today.year, today.month, today.day)
    return f"{jy}/{jm:02d}/{jd:02d}"

def jalali_to_gregorian(jy, jm, jd):
    """تبدیل شمسی به میلادی — معکوس gregorian_to_jalali بالا."""
    jy += 1595
    days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += ((jm - 7) * 30) + 186

    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1

    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0):
        g_days_in_month[1] = 29

    gm = 0
    while gm < 12 and gd > g_days_in_month[gm]:
        gd -= g_days_in_month[gm]
        gm += 1

    return gy, gm + 1, gd


PERSIAN_WEEKDAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]


def jalali_weekday_name(gregorian_date):
    """
    Python's date.weekday(): دوشنبه=0 ... یکشنبه=6 — این دقیقاً همون
    ترتیبیه که در PERSIAN_WEEKDAYS نگه داشتیم، پس نیازی به نگاشت
    اضافه نیست.
    """
    return PERSIAN_WEEKDAYS[gregorian_date.weekday()]


def full_jalali_date(gregorian_date):
    """تاریخ کامل با نام روز هفته — مثل «پنج‌شنبه ۱۲ شهریور ۱۴۰۵»."""
    PERSIAN_MONTHS = [
        "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
    ]
    jy, jm, jd = gregorian_to_jalali(gregorian_date.year, gregorian_date.month, gregorian_date.day)
    weekday = jalali_weekday_name(gregorian_date)
    return f"{weekday} {jd} {PERSIAN_MONTHS[jm - 1]} {jy}"


_PERSIAN_ONES = ["", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه"]
_PERSIAN_TENS = ["", "ده", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"]
_PERSIAN_TEENS = ["ده", "یازده", "دوازده", "سیزده", "چهارده", "پانزده", "شانزده", "هفده", "هجده", "نوزده"]
_PERSIAN_HUNDREDS = ["", "صد", "دویست", "سیصد", "چهارصد", "پانصد", "ششصد", "هفتصد", "هشتصد", "نهصد"]
_PERSIAN_SCALES = ["", "هزار", "میلیون", "میلیارد"]


def _three_digit_to_words(n):
    parts = []
    hundreds, remainder = divmod(n, 100)
    if hundreds:
        parts.append(_PERSIAN_HUNDREDS[hundreds])
    if remainder >= 10 and remainder < 20:
        parts.append(_PERSIAN_TEENS[remainder - 10])
    else:
        tens, ones = divmod(remainder, 10)
        if tens:
            parts.append(_PERSIAN_TENS[tens])
        if ones:
            parts.append(_PERSIAN_ONES[ones])
    return " و ".join(parts)


def number_to_persian_words(n):
    """تبدیل عدد صحیح به حروف فارسی — برای نمایش مبلغ به‌صورت خوانا (مثلاً «صد هزار تومان»)."""
    if n == 0:
        return "صفر"

    n = int(n)
    groups = []
    while n > 0:
        n, remainder = divmod(n, 1000)
        groups.append(remainder)

    parts = []
    for i in range(len(groups) - 1, -1, -1):
        if groups[i] == 0:
            continue
        words = _three_digit_to_words(groups[i])
        if _PERSIAN_SCALES[i]:
            words = f"{words} {_PERSIAN_SCALES[i]}"
        parts.append(words)

    return " و ".join(parts)