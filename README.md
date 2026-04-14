# Ethiopian Calendar Bot (@pagumebot)

A powerful, role-aware Telegram bot that provides date conversion, age calculation, and detailed information about the Ethiopian calendar with a robust administrative system.

## ✨ Core Features

### 👤 For Everyone
- **📅 Accurate Date Conversion:** Seamlessly flip between Gregorian and Ethiopian calendars.
- **📅 Today at a Glance:** Instant view of today's date in both systems, including Amharic weekday and month names.
- **🎂 Precision Age Calculator:** Calculate your exact age (years, months, days) using either Gregorian or Ethiopian birthdates.
- **🤝 Referral System:** Invite friends and earn rankings. Track your impact on the leaderboard!
- **📖 Educational Content:** Learn the historical and structural facts behind the unique Ethiopian calendar.
- **🌐 Multilingual:** Full support for **English** and **Amharic (አማርኛ)**.

### 👑 For Administrators (RBAC System)
The bot uses a strict Role-Based Access Control (RBAC) hierarchy:

- **Standard Users:** Access to core conversion and info tools.
- **Admins:** 
  - **📊 Unified Dashboard:** Manage users with an interactive, paginated dashboard (Filter by Activity, Joined, Referrals, or Blocked status).
  - **📢 Mass Broadcast:** Send messages to all users and group chats simultaneously.
  - **🚫 Access Control:** Block or unblock problematic users and groups from interacting with the bot.
  - **✉️ Direct Support:** Reply directly to user messages sent via the "Contact Admin" feature.
- **Super-Admins:** 
  - Full control over the administrative roster (Add/Remove/List admins).

## 🛠 Tech Stack
- **Python 3.12+**
- **python-telegram-bot** (High-level wrapper for Telegram Bot API)
- **PostgreSQL / SQLite** (Flexible database support)
- **Docker** support for containerized deployment

## 🚀 Getting Started

1. **Clone the repo:**
   ```bash
   git clone https://github.com/biluyb/Ethio-Calendar-Bot.git
   cd Ethio-Calendar-Bot
   ```

2. **Set up Environment:**
   Create a `.env` file from the provided template:
   ```env
   BOT_TOKEN=your_token_here
   ADMIN_ID=your_telegram_id
   DATABASE_URL=your_db_url (optional, defaults to SQLite)
   ```

3. **Run with Docker:**
   ```bash
   docker build -t ethio-calendar-bot .
   docker run -d --name ethio-bot --env-file .env ethio-calendar-bot
   ```

## 🤝 Contributing
Built for the Ethiopian community. Feel free to open issues or submit PRs!

## 📬 Contact
Developed by **ShademT**
- Telegram: [@pagumebot](https://t.me/pagumebot)
- © May 2026
