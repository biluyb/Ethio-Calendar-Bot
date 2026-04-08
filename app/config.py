import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Parse multiple Admin IDs if provided (comma-separated), e.g. ADMIN_IDS=123,456
admin_raw = os.getenv("ADMIN_IDS", os.getenv("ADMIN_ID", ""))
ADMIN_IDS = [int(i.strip()) for i in admin_raw.split(",") if i.strip()]
