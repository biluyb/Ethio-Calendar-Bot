from telegram import (
    BotCommand,
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from app.config import BOT_TOKEN
from app.handlers import handle, start


# =====================================================
# FULL INFORMATION TEXTS (EXACT — NO WORDS REMOVED)
# =====================================================

INFO_EN = """
ℹ️ Calendar Information
────────────────────────

1. Introduction

The Ethiopian Calendar (EC) differs from the Gregorian Calendar (GC)
in its structure and year count.

• Months:
  The Ethiopian year has 13 months.
  12 months have 30 days,
  and the 13th month (Pagume) has 5 or 6 days depending on the leap year.

• The Gap:
  There is a 7 to 8-year difference between the two calendars.

• New Year:
  Ethiopian New Year (Enkutatash) usually falls on
  September 11 (or Sept 12 in a leap year).


2. EC to GC (Ethiopian ➜ Gregorian)

To convert to Gregorian in your head,
use the 7/8 Rule:

• From Meskerem 1 to Tahsas 22 (Sept – Dec):
  Add 7 years.
    Example: 2016 EC + 7 = 2023 GC.

• From Tir 1 to Pagume (Jan – Aug):
  Add 8 years.
    Example: 2016 EC + 8 = 2024 GC.


3. GC to EC (Gregorian ➜ Ethiopian)

To bring a Gregorian date back to Ethiopian,
simply reverse the math:

• From January 1 to September 10:
  Subtract 8 years.
    Example: 2024 GC - 8 = 2016 EC.

• From September 11 to December 31:
  Subtract 7 years.
    Example: 2023 GC - 7 = 2016 EC.
"""


INFO_AM = """
ℹ️ የዘመን አቆጣጠር መረጃ
────────────────────────

1. መግቢያ (Introduction)

የኢትዮጵያ ዘመን አቆጣጠር (EC)
ከግሪጎሪያን አቆጣጠር (GC)
በዓመታት እና በወራት ስርአቱ ይለያያል

• የወራት ብዛት:
  የኢትዮጵያ አቆጣጠር 13 ወራቶች አሉት.

• የቀናት ብዛት:
  12ቱ ወራት እያንዳንዳቸው 30 ቀናት ሲኖሯቸው
  13ኛው ወር (ጳጉሜን)
  እንደ ዓመቱ ሁኔታ 5 ወይም 6 ቀናት ይኖራታል.

• ልዩነት:
  በሁለቱ አቆጣጠሮች መካከል
  የ7 ወይም 8 ዓመታት ልዩነት አለ.


2. ከኢትዮጵያ ወደ ፈረንጅ (EC to GC)

በአእምሮዎ በፍጥነት ለመቀየር
የ7/8 ደንብን ይጠቀሙ (The 7/8 Rule)

• መስከረም 1 - ታኅሣሥ 22:
  በኢትዮጵያ ዓመት ላይ 7 ይደምሩ
    ምሳሌ: 2016 ዓ.ም + 7 = 2023 እ.ኤ.አ.

• ከጥር 1 - ጳጉሜን:
  በኢትዮጵያ ዓመት ላይ 8 ይደምሩ
    ምሳሌ: 2016 ዓ.ም + 8 = 2024 እ.ኤ.አ.


3. ከፈረንጅ ወደ ኢትዮጵያ (GC to EC)

የፈረንጆቹን ዓመት ወደ ኢትዮጵያ
ለመመለስ ደንቡን ይዘርጉት

• ከጃንዋሪ (January)
  እስከ ሴፕቴምበር 10:
  ከፈረንጆች ዓመት ላይ 8 ይቀንሱ

• ከሴፕቴምበር 11 (September 11)
  እስከ ዲሴምበር:
  ከፈረንጆች ዓመት ላይ 7 ይቀንሱ
"""


# =====================================================
# PROFESSIONAL MAIN MENU (3 ROWS MODERN STYLE)
# =====================================================

def main_menu(lang: str):
    if lang == "am":
        keyboard = [
            [KeyboardButton("📅 ፈረንጅ ➜ ኢትዮጵያ")],
            [KeyboardButton("📆 ኢትዮጵያ ➜ ፈረንጅ")],
            [KeyboardButton("ℹ️ መረጃ"), KeyboardButton("🌐 ቋንቋ")]
        ]
    else:
        keyboard = [
            [KeyboardButton("📅 Gregorian ➜ Ethiopian")],
            [KeyboardButton("📆 Ethiopian ➜ Gregorian")],
            [KeyboardButton("ℹ️ Info"), KeyboardButton("🌐 Language")]
        ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# =====================================================
# LANGUAGE HANDLER
# =====================================================

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(
        [["🇺🇸 English", "🇪🇹 አማርኛ"]],
        resize_keyboard=True
    )
    await update.message.reply_text(
        "Choose language / ቋንቋ ይምረጡ",
        reply_markup=keyboard
    )


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "English" in text:
        context.user_data["lang"] = "en"
        await update.message.reply_text(
            "✅ Language set to English",
            reply_markup=main_menu("en")
        )

    elif "አማርኛ" in text:
        context.user_data["lang"] = "am"
        await update.message.reply_text(
            "✅ ቋንቋ ወደ አማርኛ ተቀይሯል",
            reply_markup=main_menu("am")
        )


# =====================================================
# INFO HANDLER (BUTTON + COMMAND)
# =====================================================

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")

    if lang == "am":
        text = " የቦት መረጃ\n\nበ biluxtech የተሰራ\n📧 biluquick123@gmail.com\n📅 May 2026"
    else:
        text = " Bot Information\n\nDeveloped by biluxtech\n📧 biluquick123@gmail.com\n© May 2026"

    await update.message.reply_text(text)

# =====================================================
# RUN APP (PROPER ASYNC COMMAND SETUP)
# =====================================================

async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Start bot"),
        BotCommand("info", "Calendar info"),
        BotCommand("lang", "Change language"),
    ])


def run():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(CommandHandler("lang", lang_command))

    # Language Selection Buttons
    app.add_handler(MessageHandler(
        filters.Regex("🇺🇸 English|🇪🇹 አማርኛ"),
        set_language
    ))

    # Main text handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("✅ Ethio Date Converter is running...")
    app.run_polling()
