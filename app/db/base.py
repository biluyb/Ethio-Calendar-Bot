import sqlite3
import os
import psycopg2
import socket
from datetime import datetime, timedelta, timezone

# Ethiopian Timezone (UTC+3)
EAT = timezone(timedelta(hours=3))

def get_eth_now():
    """Returns current Ethiopian server time formatted as a string."""
    return datetime.now(EAT).strftime('%Y-%m-%d %H:%M:%S')

# Get Database URL from environment (PostgreSQL) or fallback to SQLite
DATABASE_URL = os.getenv("DATABASE_URL")
DB_FILE = "bot.db"

# Connection Pooling for PostgreSQL
_pool = None

def get_connection():
    global _pool
    if DATABASE_URL:
        if _pool is None:
            from psycopg2.pool import ThreadedConnectionPool
            try:
                from urllib.parse import urlparse
                result = urlparse(DATABASE_URL)
                ipv4_host = socket.gethostbyname(result.hostname)
                final_url = DATABASE_URL.replace(result.hostname, ipv4_host)
            except Exception as e:
                print(f"IPv4 Resolution failed, using original URL: {e}")
                final_url = DATABASE_URL
            _pool = ThreadedConnectionPool(1, 10, final_url, sslmode="require")
        return _pool.getconn()
    else:
        conn = sqlite3.connect(DB_FILE)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

def release_connection(conn):
    if DATABASE_URL and _pool:
        _pool.putconn(conn)
    else:
        conn.close()

def init_db():
    """
    Initializes the database schema for both SQLite and PostgreSQL.
    Creates users, admins, and groups tables and performs necessary column migrations.
    """
    conn = get_connection()
    try:
        c = conn.cursor()

        # Schema definition varies slightly between SQLite (INTEGER) and PostgreSQL (BIGINT)
        if DATABASE_URL:
            # PostgreSQL Schema
            c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                lang TEXT DEFAULT 'en',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_command TEXT,
                total_actions INTEGER DEFAULT 0,
                referred_by BIGINT,
                is_blocked BOOLEAN DEFAULT FALSE,
                last_3_commands TEXT
            )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(last_active_at)")
            c.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    id BIGINT PRIMARY KEY,
                    title TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_blocked BOOLEAN DEFAULT FALSE
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id BIGINT PRIMARY KEY,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    uid BIGINT PRIMARY KEY,
                    api_key TEXT UNIQUE,
                    requests_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            # SQLite Schema
            c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                lang TEXT DEFAULT 'en',
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_active_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_command TEXT,
                total_actions INTEGER DEFAULT 0,
                referred_by INTEGER,
                is_blocked BOOLEAN DEFAULT FALSE,
                last_3_commands TEXT
            )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(last_active_at)")
            c.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_blocked BOOLEAN DEFAULT FALSE
                )
            """)
            c.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)
            c.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                uid INTEGER PRIMARY KEY,
                api_key TEXT UNIQUE,
                requests_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)

        conn.commit()
        
        # Migration: Ensure all expected columns exist
        try:
            if DATABASE_URL:
                c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users'")
                existing_cols = [row[0] for row in c.fetchall()]
                for col, stmt in [
                    ("joined_at", "ALTER TABLE users ADD COLUMN joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                    ("last_active_at", "ALTER TABLE users ADD COLUMN last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                    ("referred_by", "ALTER TABLE users ADD COLUMN referred_by BIGINT"),
                    ("is_blocked", "ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT FALSE"),
                    ("full_name", "ALTER TABLE users ADD COLUMN full_name TEXT"),
                    ("last_command", "ALTER TABLE users ADD COLUMN last_command TEXT"),
                    ("total_actions", "ALTER TABLE users ADD COLUMN total_actions INTEGER DEFAULT 0"),
                ]:
                    try:
                        if col not in existing_cols:
                            c.execute(stmt)
                    except Exception as e:
                        print(f"Failed to add {col}: {e}")
                
                # Backfill
                try:
                    c.execute("UPDATE users SET total_actions = 0 WHERE total_actions IS NULL")
                    c.execute("UPDATE users SET joined_at = CURRENT_TIMESTAMP WHERE joined_at IS NULL")
                    c.execute("UPDATE users SET last_active_at = CURRENT_TIMESTAMP WHERE last_active_at IS NULL")
                except Exception as e:
                    print(f"Backfill error: {e}")
                
                # Update groups table
                c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='groups'")
                group_cols = [row[0] for row in c.fetchall()]
                if "is_blocked" not in group_cols:
                    c.execute("ALTER TABLE groups ADD COLUMN is_blocked BOOLEAN DEFAULT FALSE")
            else:
                c.execute("PRAGMA table_info(users)")
                existing_cols = [col[1] for col in c.fetchall()]
                for col, stmt in [
                    ("joined_at", "ALTER TABLE users ADD COLUMN joined_at DATETIME DEFAULT CURRENT_TIMESTAMP"),
                    ("last_active_at", "ALTER TABLE users ADD COLUMN last_active_at DATETIME DEFAULT CURRENT_TIMESTAMP"),
                    ("referred_by", "ALTER TABLE users ADD COLUMN referred_by INTEGER"),
                    ("is_blocked", "ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT FALSE"),
                    ("full_name", "ALTER TABLE users ADD COLUMN full_name TEXT"),
                    ("last_command", "ALTER TABLE users ADD COLUMN last_command TEXT"),
                    ("total_actions", "ALTER TABLE users ADD COLUMN total_actions INTEGER DEFAULT 0"),
                ]:
                    try:
                        if col not in existing_cols:
                            c.execute(stmt)
                    except Exception as e:
                        print(f"Failed to add {col}: {e}")

                # Backfill
                try:
                    c.execute("UPDATE users SET total_actions = 0 WHERE total_actions IS NULL")
                    c.execute("UPDATE users SET joined_at = CURRENT_TIMESTAMP WHERE joined_at IS NULL")
                    c.execute("UPDATE users SET last_active_at = CURRENT_TIMESTAMP WHERE last_active_at IS NULL")
                except Exception as e:
                    print(f"Backfill error: {e}")
                
                # Update groups table
                c.execute("PRAGMA table_info(groups)")
                group_cols = [col[1] for col in c.fetchall()]
                if "is_blocked" not in group_cols:
                    c.execute("ALTER TABLE groups ADD COLUMN is_blocked BOOLEAN DEFAULT FALSE")
        except Exception as e:
            print(f"Migration error: {e}")

        conn.commit()
    except Exception as e:
        print(f"CRITICAL DB INIT ERROR: {e}")
    finally:
        release_connection(conn)
