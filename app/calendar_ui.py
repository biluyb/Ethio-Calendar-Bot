from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard(language="en"):
    if language == "am":
        keyboard = [
            [InlineKeyboardButton("ግሪጎሪያን ➜ ኢትዮጵያ", callback_data="g_to_e")],
            [InlineKeyboardButton("ኢትዮጵያ ➜ ግሪጎሪያን", callback_data="e_to_g")],
            [InlineKeyboardButton("🌐 ቋንቋ", callback_data="language")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("Gregorian ➜ Ethiopian", callback_data="g_to_e")],
            [InlineKeyboardButton("Ethiopian ➜ Gregorian", callback_data="e_to_g")],
            [InlineKeyboardButton("🌐 Language", callback_data="language")]
        ]

    return InlineKeyboardMarkup(keyboard)


def language_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="lang_am"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def restart_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔄 Start Again", callback_data="restart")]
    ]
    return InlineKeyboardMarkup(keyboard)
