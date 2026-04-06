from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(lang="en"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 GC ➜ EC", callback_data="g2e")],
        [InlineKeyboardButton("📆 EC ➜ GC", callback_data="e2g")],
        [InlineKeyboardButton("📆 Today", callback_data="today")],
        [InlineKeyboardButton("📜 History", callback_data="history")],
        [InlineKeyboardButton("🌐 Language", callback_data="lang")]
    ])
