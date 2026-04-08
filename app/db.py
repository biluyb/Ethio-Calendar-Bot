import sqlite3
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, timezone

# Ethiopian Timezone (UTC+3)
EAT = timezone(timedelta(hours=3))

def get_eth_now():
    return datetime.now(EAT).strftime('%Y-%m-%d %H:%M:%S')

# Get Database URL from environment (PostgreSQL) or fallback to SQLite
DATABASE_URL = os.getenv("DATABASE_URL")
DB_FILE = "bot.db"

def get_connection():
    if DATABASE_URL:
        # PostgreSQL
        return psycopg2.connect(DATABASE_URL, sslmode="require")
    else:
        # SQLite
        return sqlite3.connect(DB_FILE)

# ================== INIT ==================

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # PostgreSQL uses SERIAL for autoincrement, SQLite uses AUTOINCREMENT
    # Using logical structure that fits both where possible
    
    # 1. USERS TABLE
    if DATABASE_URL:
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            username TEXT,
            lang TEXT DEFAULT 'en',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(last_active_at)")
    else:
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            lang TEXT DEFAULT 'en',
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_active_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(last_active_at)")

    # 2. ADMINS TABLE
    if DATABASE_URL:
        c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id BIGINT PRIMARY KEY,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    else:
        c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
    
    conn.commit()
    
    # Simple migration for existing users table
    try:
        if DATABASE_URL:
            # PostgreSQL migration
            c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users'")
            existing_cols = [row[0] for row in c.fetchall()]
            if "joined_at" not in existing_cols:
                c.execute("ALTER TABLE users ADD COLUMN joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            if "last_active_at" not in existing_cols:
                c.execute("ALTER TABLE users ADD COLUMN last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        else:
            # SQLite migration
            c.execute("PRAGMA table_info(users)")
            existing_cols = [col[1] for col in c.fetchall()]
            if "joined_at" not in existing_cols:
                try:
                    c.execute("ALTER TABLE users ADD COLUMN joined_at DATETIME DEFAULT CURRENT_TIMESTAMP")
                except Exception:
                    c.execute("ALTER TABLE users ADD COLUMN joined_at DATETIME")
                    c.execute("UPDATE users SET joined_at = CURRENT_TIMESTAMP")
            if "last_active_at" not in existing_cols:
                try:
                    c.execute("ALTER TABLE users ADD COLUMN last_active_at DATETIME DEFAULT CURRENT_TIMESTAMP")
                except Exception:
                    c.execute("ALTER TABLE users ADD COLUMN last_active_at DATETIME")
                    c.execute("UPDATE users SET last_active_at = CURRENT_TIMESTAMP")
    except Exception as e:
        print(f"Migration error: {e}")

    conn.commit()
    conn.close()

def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY last_active_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def search_users(query, sort_by="last_active_at"):
    conn = get_connection()
    c = conn.cursor()
    # SQL injection safe query
    q = f"%{query}%"
    
    order_clause = "last_active_at DESC"
    if sort_by == "joined_at":
        order_clause = "joined_at DESC"
    
    if DATABASE_URL:
        c.execute(f"SELECT * FROM users WHERE username ILIKE %s OR CAST(id AS TEXT) LIKE %s ORDER BY {order_clause}", (q, q))
    else:
        c.execute(f"SELECT * FROM users WHERE username LIKE ? OR CAST(id AS TEXT) LIKE ? ORDER BY {order_clause}", (q, q))
    rows = c.fetchall()
    conn.close()
    return rows

# ================== USER ==================

def register_user(uid, username):
    conn = get_connection()
    c = conn.cursor()

    now = get_eth_now()
    if DATABASE_URL:
        c.execute("SELECT id FROM users WHERE id=%s", (uid,))
        if not c.fetchone():
            c.execute("INSERT INTO users (id, username, joined_at, last_active_at) VALUES (%s, %s, %s, %s)", (uid, username, now, now))
        else:
            c.execute("UPDATE users SET username=%s, last_active_at=%s WHERE id=%s", (username, now, uid))
    else:
        c.execute("SELECT id FROM users WHERE id=?", (uid,))
        if not c.fetchone():
            c.execute("INSERT INTO users (id, username, joined_at, last_active_at) VALUES (?, ?, ?, ?)", (uid, username, now, now))
        else:
            c.execute("UPDATE users SET username=?, last_active_at=? WHERE id=?", (username, now, uid))

    conn.commit()
    conn.close()

def get_lang(uid):
    conn = get_connection()
    c = conn.cursor()

    if DATABASE_URL:
        c.execute("SELECT lang FROM users WHERE id=%s", (uid,))
    else:
        c.execute("SELECT lang FROM users WHERE id=?", (uid,))
    
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else "en"

def set_lang(uid, lang):
    conn = get_connection()
    c = conn.cursor()

    if DATABASE_URL:
        c.execute("UPDATE users SET lang=%s WHERE id=%s", (lang, uid))
    else:
        c.execute("UPDATE users SET lang=? WHERE id=?", (lang, uid))

    conn.commit()
    conn.close()

    
def get_user(update):
    user = update.effective_user
    return user.username or user.first_name or str(user.id)

# ================== ADMINS ==================

def is_admin_db(uid):
    conn = get_connection()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute("SELECT id FROM admins WHERE id=%s", (uid,))
    else:
        c.execute("SELECT id FROM admins WHERE id=?", (uid,))
    res = c.fetchone()
    conn.close()
    return True if res else False

def get_admins_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM admins")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def add_admin_db(uid):
    conn = get_connection()
    c = conn.cursor()
    now = get_eth_now()
    try:
        if DATABASE_URL:
            c.execute("INSERT INTO admins (id, added_at) VALUES (%s, %s) ON CONFLICT DO NOTHING", (uid, now))
        else:
            c.execute("INSERT INTO admins (id, added_at) VALUES (?, ?)", (uid, now))
        conn.commit()
    except Exception:
        pass # Already exists
    conn.close()

def remove_admin_db(uid):
    conn = get_connection()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute("DELETE FROM admins WHERE id=%s", (uid,))
    else:
        c.execute("DELETE FROM admins WHERE id=?", (uid,))
    conn.commit()
    conn.close()
