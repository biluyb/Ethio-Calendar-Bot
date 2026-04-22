# Ethiopian Calendar Bot (@pagumebot)

Welcome to the **Ethiopian Calendar Bot**! This is the most advanced and comprehensive Telegram bot built for date conversion, age calculation, and Ethiopian calendar logic. With over thousands of users, it provides robust features wrapped in a user-friendly bilingual interface.

## Core Features 🚀

### 1. Bilingual Support (English & Amharic)
The bot natively supports both Amharic and English. Users can seamlessly switch between languages using the `/lang` command, and all menus, buttons, and calendar outputs adapt instantly. 

### 2. Powerful Date Conversion 📅
- Convert dates from **Gregorian to Ethiopian** calendar.
- Convert dates from **Ethiopian to Gregorian** calendar.
- Outputs include full weekday and month names in both English and Amharic.
- The `/today` command gives an instant summary of today's date in both calendar systems.

### 3. Precise Age Calculation 🎂
Users can easily calculate their exact age in years, months, and days. The bot determines the age accurately whether you provide an Ethiopian or Gregorian birthdate. 

### 4. Referral & Ranking System 🏆
We believe in community! Every user gets a unique referral link via the `/share` command. Inviting friends awards points, and users can check the leaderboard using the `/ranks` command to see the top referrers.

### 5. Seamless Group Integration 🏘️
The bot can be added to Telegram groups. It has a smart redirect feature that ensures group chats stay clean, guiding users to interact with it via Direct Messages for complex requests. 

---

## Administrative Tools & RBAC 🛡️

Pagume Bot features a highly sophisticated **Role-Based Access Control (RBAC)** architecture directly within Telegram. It dynamically refreshes the bot's command menus depending on whether the user is a standard user, an Admin, or a Super-Admin.

### Admin Capabilities (`/users`, `/broadcast`, etc.)
- **User Dashboard (`/users`):** View an inline, paginated list of all users. Sort them by activity, join date, or referral counts. See detailed profiles of any user.
- **Mass Broadcast (`/broadcast`):** Instantly send announcements to all users and registered group chats at the same time.
- **Direct Messaging (`/send_msg`):** Admins can directly chat with users through the bot by providing their User ID or Username.
- **Bot Access Control (`/block`, `/unblock`):** Admins can restrict malicious users or groups from interacting with the bot.
- **Group Management (`/groups`, `/leavegroup`):** Track which groups the bot is in and forcefully remove the bot from unwanted groups.

### Super-Admin Privileges
Super-Admins have exclusive rights to manage the administrative roster:
- `/addadmin` to promote users to Admin.
- `/deladmin` to demote Admins.
- `/listadmins` to view the current list of authorized managers.

---

## API Capabilities 🌐

The bot double-functions as a RESTful API service! It exposes versioned endpoints to developers who want Ethiopian calendar functionality in their own apps. 
- **API Key Generation:** Users can generate API keys directly inside Telegram using the `/api` command.
- **Endpoints:** `/v1/convert`, `/v1/today`, and `/v1/age`.
- **Security:** Requires Bearer Token Authentication and enforces strict rate-limiting (30 requests per minute). 
- **Analytics (`/api_stats`):** Admins can monitor live API usage statistics and revoke abusive keys.

---

## Technical Stack & Architecture ⚙️

- **Framework:** Written in Python 3.12+ relying on the powerful `python-telegram-bot` standard.
- **Asynchronous Processing:** Built over `asyncio` for high concurrency.
- **Web App:** Uses `aiohttp` to run a webhook-based production web server and an interactive landing page on Render.
- **Database:** Features an abstracted Database Layer. Seamlessly utilizes **SQLite** for zero-configuration local development and scales gracefully using **PostgreSQL** in production environments.
- **Deployment:** Fully Dockerized (`Dockerfile`) for reproducible environments and zero-downtime deployment. 

## Run it Yourself

1. **Clone & Setup:**
   ```bash
   git clone https://github.com/biluyb/Ethio-Calendar-Bot.git
   cd Ethio-Calendar-Bot
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Variables:**
   Create a `.env` file referencing your `BOT_TOKEN`, `ADMIN_IDS`, and `DATABASE_URL` (if using Postgres).

3. **Deploy (Docker):**
   ```bash
   docker build -t ethio-bot .
   docker run -d --env-file .env ethio-bot
   ```

## Contributions & Credits 🤝
Built with passion by ShademT. Open for issues and pull requests to expand our calendar ecosystem!

*© 2026 — Telegram: [@pagumebot](https://t.me/pagumebot)*
