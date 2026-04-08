from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from app.config import BOT_TOKEN
from app.handlers import start, handle, lang, bot_info 
from app.handlers import notify_admin


async def error_handler(update, context):
    print(f"GLOBAL ERROR: {context.error}")
    error_msg = f"Global Error:\n{context.error}"
    print(error_msg)

    await notify_admin(context, error_msg)

from app.db import init_db

def main():
    # Initialize Database
    init_db()

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .build()
    )


    # COMMANDS
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang", lang))
    app.add_handler(CommandHandler("info", bot_info))
    from app.handlers import users, users_callback, age_mode_callback
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CallbackQueryHandler(users_callback, pattern="^u:"))
    app.add_handler(CallbackQueryHandler(age_mode_callback, pattern="^age_mode_"))

    # TEXT HANDLER
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_error_handler(error_handler)

    print("✅ Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
