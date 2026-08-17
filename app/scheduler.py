"""
Background Reminder Scheduler
Periodically checks for due reminders and dispatches Telegram notifications to users.
"""

import asyncio
from telegram.ext import Application
from app.db.reminder_db import get_due_reminders, mark_reminder_triggered
from app.db import get_lang
from app.utils import eth_to_greg

ETH_MONTHS_AM = [
    "መስከረም", "ጥቅምት", "ኅዳር", "ታኅሣሥ",
    "ጥር", "የካቲት", "መጋቢት", "ሚያዝያ",
    "ግንቦት", "ሰኔ", "ሐምሌ", "ነሐሴ", "ጳጉሜ"
]

ETH_MONTHS_EN = [
    "Meskerem", "Tikimt", "Hidar", "Tahsas",
    "Tir", "Yekatit", "Megabit", "Miyazia",
    "Ginbot", "Sene", "Hamle", "Nehase", "Pagume"
]


async def reminder_checker_loop(app: Application):
    """Loop that runs in the background checking for due reminders every 60 seconds."""
    while True:
        try:
            due = get_due_reminders()
            for rem_id, user_id, eth_year, eth_month, eth_day, greg_date, message in due:
                try:
                    lang = get_lang(user_id)
                    m_am = ETH_MONTHS_AM[eth_month - 1]
                    m_en = ETH_MONTHS_EN[eth_month - 1]

                    if lang == "am":
                        text = (
                            f"⏰ <b>የቀን ማስታወቂያ (Reminder)!</b>\n\n"
                            f"📅 ቀን፦ <b>{m_am} {eth_day}፣ {eth_year} ዓ.ም</b>\n"
                            f"📆 ፈረንጅ፦ <b>{greg_date}</b>\n\n"
                            f"📝 <b>ማስታወሻዎ፦</b>\n"
                            f"<i>{message}</i>"
                        )
                    else:
                        text = (
                            f"⏰ <b>Calendar Reminder Notification!</b>\n\n"
                            f"📅 Date: <b>{m_en} {eth_day}, {eth_year} E.C.</b>\n"
                            f"📆 Gregorian: <b>{greg_date}</b>\n\n"
                            f"📝 <b>Your Reminder Note:</b>\n"
                            f"<i>{message}</i>"
                        )

                    await app.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        parse_mode="HTML"
                    )
                    mark_reminder_triggered(rem_id)
                except Exception as send_err:
                    print(f"Failed to send reminder {rem_id} to {user_id}: {send_err}")
                    # If user blocked bot or deleted chat, mark triggered to prevent infinite retry
                    if "blocked" in str(send_err).lower() or "deactivated" in str(send_err).lower():
                        mark_reminder_triggered(rem_id)
        except Exception as e:
            print(f"Error in reminder loop: {e}")

        # Check every 60 seconds
        await asyncio.sleep(60)


def start_scheduler(app: Application):
    """Starts the background scheduler task in the application asyncio event loop."""
    asyncio.create_task(reminder_checker_loop(app))
