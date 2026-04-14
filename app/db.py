import sqlite3
import os
import psycopg2
import socket
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, timezone

# Ethiopian Timezone (UTC+3)
EAT = timezone(timedelta(hours=3))

def get_eth_now():
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
            # Attempt to resolve hostname to IPv4 to bypass Render's IPv6 issues
            try:
                # Example: postgresql://user:pass@host:port/db
                from urllib.parse import urlparse
                result = urlparse(DATABASE_URL)
                ipv4_host = socket.gethostbyname(result.hostname)
                # Replace hostname with IP in the URL to force IPv4
                final_url = DATABASE_URL.replace(result.hostname, ipv4_host)
            except Exception as e:
                print(f"IPv4 Resolution failed, using original URL: {e}")
                final_url = DATABASE_URL
                
            # Pool: min 1 connection, max 10
            # Higher minconn causes slower cold starts on Render
            _pool = ThreadedConnectionPool(1, 10, final_url, sslmode="require")
        return _pool.getconn()
    else:
        # SQLite
        conn = sqlite3.connect(DB_FILE)
        # Enable WAL mode for high concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

def release_connection(conn):
    if DATABASE_URL and _pool:
        _pool.putconn(conn)
    else:
        conn.close()

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
            last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            referred_by BIGINT
        )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(last_active_at)")
        c.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id BIGINT PRIMARY KEY,
                title TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            lang TEXT DEFAULT 'en',
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_active_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            referred_by INTEGER
        )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(last_active_at)")
        c.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY,
                title TEXT,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

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
            if "referred_by" not in existing_cols:
                c.execute("ALTER TABLE users ADD COLUMN referred_by BIGINT")
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
            if "referred_by" not in existing_cols:
                c.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
    except Exception as e:
        print(f"Migration error: {e}")

    conn.commit()
    release_connection(conn)

def get_all_user_ids():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users")
    rows = c.fetchall()
    release_connection(conn)
    return [r[0] for r in rows]

def get_all_users(sort_by="last_active_at", limit=None, offset=None):
    conn = get_connection()
    c = conn.cursor()
    
    order_clause = "last_active_at DESC"
    if sort_by == "joined_at":
        order_clause = "joined_at DESC"
    elif sort_by == "referrals":
        order_clause = "referral_count DESC"
        
    query = f"""
        SELECT u.*, (SELECT COUNT(*) FROM users WHERE referred_by = u.id) as referral_count 
        FROM users u 
        ORDER BY {order_clause}
    """
    params = []
    
    if limit is not None:
        query += " LIMIT %s" if DATABASE_URL else " LIMIT ?"
        params.append(limit)
    if offset is not None:
        query += " OFFSET %s" if DATABASE_URL else " OFFSET ?"
        params.append(offset)
        
    c.execute(query, tuple(params))
    rows = c.fetchall()
    release_connection(conn)
    return rows

def search_users(query, sort_by="last_active_at", limit=None, offset=None):
    conn = get_connection()
    c = conn.cursor()
    # SQL injection safe query
    q = f"%{query}%"
    
    order_clause = "last_active_at DESC"
    if sort_by == "joined_at":
        order_clause = "joined_at DESC"
    elif sort_by == "referrals":
        order_clause = "referral_count DESC"
    
    base_query = f"""
        SELECT u.*, (SELECT COUNT(*) FROM users WHERE referred_by = u.id) as referral_count 
        FROM users u 
        WHERE u.username {'ILIKE' if DATABASE_URL else 'LIKE'} %s 
        OR CAST(u.id AS TEXT) LIKE %s
    """ if DATABASE_URL else f"""
        SELECT u.*, (SELECT COUNT(*) FROM users WHERE referred_by = u.id) as referral_count 
        FROM users u 
        WHERE u.username LIKE ? 
        OR CAST(u.id AS TEXT) LIKE ?
    """
    
    sql = f"{base_query} ORDER BY {order_clause}"
    params = [q, q]
    
    if limit is not None:
        sql += " LIMIT %s" if DATABASE_URL else " LIMIT ?"
        params.append(limit)
    if offset is not None:
        sql += " OFFSET %s" if DATABASE_URL else " OFFSET ?"
        params.append(offset)

    c.execute(sql, tuple(params))
    rows = c.fetchall()
    release_connection(conn)
    return rows

def get_user_count(search_query=None):
    conn = get_connection()
    c = conn.cursor()
    
    if search_query:
        q = f"%{search_query}%"
        if DATABASE_URL:
            c.execute("SELECT COUNT(*) FROM users WHERE username ILIKE %s OR CAST(id AS TEXT) LIKE %s", (q, q))
        else:
            c.execute("SELECT COUNT(*) FROM users WHERE username LIKE ? OR CAST(id AS TEXT) LIKE ?", (q, q))
    else:
        c.execute("SELECT COUNT(*) FROM users")
        
    count = c.fetchone()[0]
    release_connection(conn)
    return count

def get_user_by_id(uid):
    conn = get_connection()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute("SELECT * FROM users WHERE id=%s", (uid,))
    else:
        c.execute("SELECT * FROM users WHERE id=?", (uid,))
    row = c.fetchone()
    release_connection(conn)
    return row

def get_user_by_username(username):
    conn = get_connection()
    c = conn.cursor()
    # Normalize username (strip @ if present)
    uname = username.lstrip("@")
    if DATABASE_URL:
        c.execute("SELECT * FROM users WHERE username ILIKE %s", (uname,))
    else:
        c.execute("SELECT * FROM users WHERE username LIKE ?", (uname,))
    row = c.fetchone()
    release_connection(conn)
    return row

# ================== USER ==================

def register_user(uid, username, referred_by=None):
    conn = get_connection()
    c = conn.cursor()

    now = get_eth_now()
    is_new = False
    if DATABASE_URL:
        c.execute("SELECT id FROM users WHERE id=%s", (uid,))
        if not c.fetchone():
            c.execute("INSERT INTO users (id, username, joined_at, last_active_at, referred_by) VALUES (%s, %s, %s, %s, %s)", (uid, username, now, now, referred_by))
            is_new = True
        else:
            c.execute("UPDATE users SET username=%s, last_active_at=%s WHERE id=%s", (username, now, uid))
    else:
        c.execute("SELECT id FROM users WHERE id=?", (uid,))
        if not c.fetchone():
            c.execute("INSERT INTO users (id, username, joined_at, last_active_at, referred_by) VALUES (?, ?, ?, ?, ?)", (uid, username, now, now, referred_by))
            is_new = True
        else:
            c.execute("UPDATE users SET username=?, last_active_at=? WHERE id=?", (username, now, uid))

    conn.commit()
    release_connection(conn)
    return is_new

def get_lang(uid):
    conn = get_connection()
    c = conn.cursor()

    if DATABASE_URL:
        c.execute("SELECT lang FROM users WHERE id=%s", (uid,))
    else:
        c.execute("SELECT lang FROM users WHERE id=?", (uid,))
    
    row = c.fetchone()
    release_connection(conn)
    return row[0] if row and row[0] else "en"

def get_top_referrers(limit=10, offset=0):
    conn = get_connection()
    c = conn.cursor()
    
    if DATABASE_URL:
        query = """
            SELECT u.id, u.username, (SELECT COUNT(*) FROM users WHERE referred_by = u.id) as ref_count
            FROM users u
            WHERE (SELECT COUNT(*) FROM users WHERE referred_by = u.id) > 0
            ORDER BY ref_count DESC
            LIMIT %s OFFSET %s
        """
        c.execute(query, (limit, offset))
    else:
        query = """
            SELECT u.id, u.username, (SELECT COUNT(*) FROM users WHERE referred_by = u.id) as ref_count
            FROM users u
            WHERE (SELECT COUNT(*) FROM users WHERE referred_by = u.id) > 0
            ORDER BY ref_count DESC
            LIMIT ? OFFSET ?
        """
        c.execute(query, (limit, offset))
        
    rows = c.fetchall()
    release_connection(conn)
    return rows

def get_referrers_count():
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT COUNT(DISTINCT referred_by) FROM users WHERE referred_by IS NOT NULL"
    c.execute(query)
    count = c.fetchone()[0]
    release_connection(conn)
    return count

def set_lang(uid, lang):
    conn = get_connection()
    c = conn.cursor()

    if DATABASE_URL:
        c.execute("UPDATE users SET lang=%s WHERE id=%s", (lang, uid))
    else:
        c.execute("UPDATE users SET lang=? WHERE id=?", (lang, uid))

    conn.commit()
    release_connection(conn)
    
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
    release_connection(conn)
    return True if res else False

def get_admins_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM admins")
    rows = c.fetchall()
    release_connection(conn)
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
    release_connection(conn)

def remove_admin_db(uid):
    conn = get_connection()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute("DELETE FROM admins WHERE id=%s", (uid,))
    else:
        c.execute("DELETE FROM admins WHERE id=?", (uid,))
    conn.commit()
    release_connection(conn)

# ================== GROUPS ==================

def register_group(group_id, title):
    conn = get_connection()
    c = conn.cursor()
    now = get_eth_now()
    if DATABASE_URL:
        c.execute("INSERT INTO groups (id, title, joined_at) VALUES (%s, %s, %s) ON CONFLICT (id) DO UPDATE SET title=%s", (group_id, title, now, title))
    else:
        c.execute("SELECT id FROM groups WHERE id=?", (group_id,))
        if not c.fetchone():
            c.execute("INSERT INTO groups (id, title, joined_at) VALUES (?, ?, ?)", (group_id, title, now))
        else:
            c.execute("UPDATE groups SET title=? WHERE id=?", (title, group_id))
    conn.commit()
    release_connection(conn)

def get_all_group_ids():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM groups")
    rows = c.fetchall()
    release_connection(conn)
    return [r[0] for r in rows]
    release_connection(conn)
