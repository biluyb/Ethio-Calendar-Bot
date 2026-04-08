# Ethio Calendar Bot (@pagumebot)

A Python-based Telegram bot for converting dates between the Ethiopian and Gregorian calendars.

## Features

- Conversion from Gregorian to Ethiopian calendar.
- Conversion from Ethiopian to Gregorian calendar.
- 🎂 **Age Calculator**: Exact age breakdown in Years, Months, and Days.
- Real-time display of today's date in both calendar systems.
- Bilingual interface supporting English and Amharic.
- Admin dashboard for user statistics with search and pagination.
- Multi-admin support.

## Usage

The bot can be found on Telegram at @pagumebot or use the link https://t.me/pagumebot. Users can start the bot using the /start command, select their preferred language, and then choose a conversion method from the menu. Dates should be entered in the DD/MM/YYYY format.

## Implementation Details

- Language: Python 3.12+
- Library: python-telegram-bot
- Database: SQLite3
- Configuration: Environment variables via .env

## Local Setup

To run this project locally, follow these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/biluyb/Ethio-Calendar-Bot.git
   cd Ethio-Calendar-Bot
   ```

2. Configure a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a .env file in the root directory with the following variables:
   ```env
   BOT_TOKEN=your_bot_token
   ADMIN_ID=your_id
   ```

5. Start the bot:
   ```bash
   python run.py
   ```

## Contact

Developed by ShademT
Email: biluquick123@gmail.com
Copyright May 2026
