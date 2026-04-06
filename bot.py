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
# MAIN MENU
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
# LANGUAGE COMMAND
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
# INFO COMMAND (UPDATED AS YOU REQUESTED)
# =====================================================

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Bot Information\n"
        "────────────────────────\n\n"
        "Developed by BiluxTech\n"
        "Contact: biluquick123@gmail.com\n"
        "Date: May 2026"
    )


# =====================================================
# BUTTON HANDLER (CONNECT BUTTONS TO COMMANDS)
# =====================================================

async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text in ["🌐 Language", "🌐 ቋንቋ"]:
        return await lang_command(update, context)

    elif text in ["ℹ️ Info", "ℹ️ መረጃ"]:
        return await info_command(update, context)


# =====================================================
# COMMAND MENU (TELEGRAM MENU)
# =====================================================

async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Start bot"),
        BotCommand("info", "Calendar info"),
        BotCommand("lang", "Change language"),
    ])


# =====================================================
# RUN BOT
# =====================================================

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

    # Language selection
    app.add_handler(MessageHandler(
        filters.Regex("🇺🇸 English|🇪🇹 አማርኛ"),
        set_language
    ))

    # Button routing (IMPORTANT)
    app.add_handler(MessageHandler(
        filters.Regex("🌐 Language|🌐 ቋንቋ|ℹ️ Info|ℹ️ መረጃ"),
        button_router
    ))

    # Main logic
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("✅ Bot running...")
    app.run_polling()
