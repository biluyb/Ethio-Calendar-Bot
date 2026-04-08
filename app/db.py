import sqlite3
import os
import psycopg2
from psycopg2.extras import RealDictCursor

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
        
        # 2. HISTORY TABLE
        c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id SERIAL PRIMARY KEY,
            username BIGINT,
            text TEXT
        )
        """)
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
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username INTEGER,
            text TEXT
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

    if DATABASE_URL:
        c.execute("SELECT id FROM users WHERE id=%s", (uid,))
        if not c.fetchone():
            c.execute("INSERT INTO users (id, username, joined_at, last_active_at) VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)", (uid, username))
        else:
            c.execute("UPDATE users SET username=%s, last_active_at=CURRENT_TIMESTAMP WHERE id=%s", (username, uid))
    else:
        c.execute("SELECT id FROM users WHERE id=?", (uid,))
        if not c.fetchone():
            c.execute("INSERT INTO users (id, username, joined_at, last_active_at) VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)", (uid, username))
        else:
            c.execute("UPDATE users SET username=?, last_active_at=CURRENT_TIMESTAMP WHERE id=?", (username, uid))

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

# ================== HISTORY ==================

def save_history(uid, text):
    conn = get_connection()
    c = conn.cursor()

    if DATABASE_URL:
        c.execute("INSERT INTO history (username, text) VALUES (%s, %s)", (uid, text))
    else:
        c.execute("INSERT INTO history (username, text) VALUES (?, ?)", (uid, text))

    conn.commit()
    conn.close()

def get_history(uid):
    conn = get_connection()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute("SELECT text FROM history WHERE username=%s", (uid,))
    else:
        c.execute("SELECT text FROM history WHERE username=?", (uid,))
    data = [x[0] for x in c.fetchall()]
    conn.close()
    return data
    
def get_user(update):
    user = update.effective_user
    return user.username or user.first_name or str(user.id)
