# Ethiopian Calendar Bot (@pagumebot)

This is a simple but powerful Telegram bot that helps you convert dates between the Ethiopian and Gregorian calendars. It also calculates age precisely and provides historical info about the Ethiopian calendar.

## What it does

### For Everyone
- **Convert Dates:** Quickly flip between Gregorian and Ethiopian dates.
- **Check Today:** See what today's date is in both systems, including Amharic weekday and month names.
- **Calculate Age:** Find out exactly how old you are in years, months, and days using either your Gregorian or Ethiopian birthdate.
- **Learn:** Use `/info` to learn some interesting facts about how the Ethiopian calendar works.
- **Two Languages:** Works in both English and Amharic (አማርኛ).

### For Admins
- **Manage Users:** View stats and search for users directly through a dashboard.
- **Admin Tools:** Add or remove other admins with simple commands.
- **Direct Support:** Users can message the admin through the bot, and admins can reply back directly.
- **Health Checks:** The bot automatically alerts admins if something goes wrong.

## Tech Stack
- **Python 3.12+**
- **python-telegram-bot**
- **SQLite3** for the database
- **Docker** support for easy hosting

## How to run it locally

1. **Clone the repo:**
   ```bash
   git clone https://github.com/biluyb/Ethio-Calendar-Bot.git
   cd Ethio-Calendar-Bot
   ```

2. **Set up a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Add your tokens:**
   Create a `.env` file and add your bot token and admin ID:
   ```env
   BOT_TOKEN=your_token_here
   ADMIN_ID=your_telegram_id
   ```

5. **Run the bot:**
   ```bash
   python run.py
   ```

## Running with Docker
If you prefer Docker, you can use:
```bash
docker build -t ethio-calendar-bot .
docker run -d --name ethio-bot --env-file .env ethio-calendar-bot
```

## Contact
Developed by **ShademT**
- Telegram: [@pagumebot](https://t.me/pagumebot)
- Email: biluquick123@gmail.com
- © May 2026

---
*Built for the Ethiopian community.*
