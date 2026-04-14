# Ethiopian Calendar Bot (@pagumebot)

A comprehensive Telegram bot designed for date conversion, age calculation, and cultural information regarding the Ethiopian calendar. The bot includes a robust administrative system with role-based access control to manage users and system interactions.

## Core Features

### For All Users
- **Accurate Date Conversion:** Easily convert dates between the Gregorian and Ethiopian calendars.
- **Daily Information:** View today's date in both systems, including Amharic weekday and month names.
- **Age Calculation:** Determine your precise age in years, months, and days using either Gregorian or Ethiopian birthdates.
- **Referral System:** Invite others and track your impact through a ranking system and leaderboard.
- **Educational Resources:** Access historical and structural facts about the Ethiopian calendar system.
- **Multilingual Support:** Full functionality in both English and Amharic.

### Administrative Tools (RBAC)
The bot implements a Role-Based Access Control system to ensure secure and efficient management:

- **Standard Users:** Access to core conversion and informational features.
- **Admins:** 
  - **Unified Dashboard:** An interactive, paginated interface to manage users, with sorting options for activity, join date, referrals, and blocked status.
  - **Mass Broadcasting:** Send announcements to all individual users and registered group chats.
  - **Access Management:** Block or unblock users and groups to maintain bot health and security.
  - **Direct Support:** Reply to user inquiries sent through the contact feature directly.
- **Super-Admins:** 
  - Complete control over the administrative roster, including adding, removing, and listing authorized admins.

## Technical Specifications
- **Core:** Python 3.12+
- **Library:** python-telegram-bot
- **Database:** Support for both PostgreSQL and SQLite
- **Deployment:** Docker support for containerized environments

## Installation and Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/biluyb/Ethio-Calendar-Bot.git
   cd Ethio-Calendar-Bot
   ```

2. **Environment Configuration:**
   Create a `.env` file with the following variables:
   ```env
   BOT_TOKEN=your_telegram_bot_token
   ADMIN_ID=your_primary_admin_id
   DATABASE_URL=your_database_connection_string (optional)
   ```

3. **Deploy with Docker:**
   ```bash
   docker build -t ethio-calendar-bot .
   docker run -d --name ethio-bot --env-file .env ethio-calendar-bot
   ```

## Contributions
This project is developed for the Ethiopian community. Issues and pull requests are welcome.

## Contact and Credits
Developed by ShademT.
- Telegram: [@pagumebot](https://t.me/pagumebot)
- © May 2026
