"""
Database Access Layer for Ethiopian Calendar Bot.
Supports both SQLite (local development) and PostgreSQL (production via Supabase).
Implements connection pooling for PostgreSQL to manage resources efficiently.
"""

import sqlite3
import os
import psycopg2
import socket
import secrets
from psycopg2.extras import RealDictCursor
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
                is_blocked BOOLEAN DEFAULT FALSE
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
                is_blocked BOOLEAN DEFAULT FALSE
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

def get_all_user_ids():
    """Returns a list of all user IDs from the database."""
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT id FROM users")
        rows = c.fetchall()
        return [r[0] for r in rows]
    except Exception as e:
        print(f"Error fetching user IDs: {e}")
        return []
    finally:
        release_connection(conn)

def get_all_users(sort_by="last_active_at", order="DESC", limit=None, offset=None):
    """Retrieves all users with optional filtering for blocked status and dynamic ordering."""
    conn = get_connection()
    try:
        c = conn.cursor()
        
        # Validate order to prevent SQL injection
        order = "ASC" if order.upper() == "ASC" else "DESC"
        
        field = "last_active_at"
        if sort_by == "joined_at":
            field = "joined_at"
        elif sort_by == "referrals":
            field = "referral_count"
            
        order_clause = f"{field} {order}"
        
        where_clause = ""
        if sort_by == "blocked":
            where_clause = "WHERE u.is_blocked = TRUE" if DATABASE_URL else "WHERE u.is_blocked = 1"
        
        query = f"""
            SELECT 
                u.id, u.username, u.full_name, u.lang, u.joined_at, 
                u.last_active_at, u.last_command, u.total_actions, 
                u.referred_by, u.is_blocked,
                (SELECT COUNT(*) FROM users WHERE referred_by = u.id) as referral_count 
            FROM users u 
            {where_clause}
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
        return c.fetchall()
    except Exception as e:
        print(f"Error in get_all_users: {e}")
        return []
    finally:
        release_connection(conn)

def search_users(query, sort_by="last_active_at", order="DESC", limit=None, offset=None):
    """Searches users with support for blocked filtering, sorting, and dynamic ordering."""
    conn = get_connection()
    try:
        c = conn.cursor()
        q = f"%{query}%"
        
        # Validate order to prevent SQL injection
        order = "ASC" if order.upper() == "ASC" else "DESC"
        
        field = "last_active_at"
        if sort_by == "joined_at":
            field = "joined_at"
        elif sort_by == "referrals":
            field = "referral_count"
            
        order_clause = f"{field} {order}"

        filter_blocked = (sort_by == "blocked")
        where_conds = []
        if filter_blocked:
            where_conds.append("u.is_blocked = TRUE" if DATABASE_URL else "u.is_blocked = 1")
        
        search_part = f"(u.username {'ILIKE' if DATABASE_URL else 'LIKE'} %s OR CAST(u.id AS TEXT) LIKE %s)" if DATABASE_URL else "(u.username LIKE ? OR CAST(u.id AS TEXT) LIKE ?)"
        where_conds.append(search_part)
        where_clause = "WHERE " + " AND ".join(where_conds)
            
        base_query = f"""
            SELECT u.*, (SELECT COUNT(*) FROM users WHERE referred_by = u.id) as referral_count 
            FROM users u 
            {where_clause}
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
        return c.fetchall()
    except Exception as e:
        print(f"Error in search_users: {e}")
        return []
    finally:
        release_connection(conn)

def get_user_count(search_query=None, filter_blocked=False):
    """Returns the total number of users, optionally filtered by search and block status."""
    conn = get_connection()
    try:
        c = conn.cursor()
        where_conds = []
        params = []
        
        if filter_blocked:
            where_conds.append("is_blocked = TRUE" if DATABASE_URL else "is_blocked = 1")
            
        if search_query:
            q = f"%{search_query}%"
            search_cond = "(username ILIKE %s OR CAST(id AS TEXT) LIKE %s)" if DATABASE_URL else "(username LIKE ? OR CAST(id AS TEXT) LIKE ?)"
            where_conds.append(search_cond)
            params.extend([q, q])
            
        sql = "SELECT COUNT(*) FROM users"
        if where_conds:
            sql += " WHERE " + " AND ".join(where_conds)
            
        c.execute(sql, tuple(params))
        return c.fetchone()[0]
    except Exception as e:
        print(f"Error in get_user_count: {e}")
        return 0
    finally:
        release_connection(conn)

def get_user_by_id(uid):
    """Retrieves full user data by unique ID."""
    conn = get_connection()
    try:
        c = conn.cursor()
        if DATABASE_URL:
            c.execute("SELECT * FROM users WHERE id=%s", (uid,))
        else:
            c.execute("SELECT * FROM users WHERE id=?", (uid,))
        return c.fetchone()
    except Exception as e:
        print(f"Error in get_user_by_id: {e}")
        return None
    finally:
        release_connection(conn)

def get_user_by_username(username):
    """Retrieves full user data by username (case-insensitive on Postgres)."""
    conn = get_connection()
    try:
        c = conn.cursor()
        uname = username.lstrip("@")
        if DATABASE_URL:
            c.execute("SELECT * FROM users WHERE username ILIKE %s", (uname,))
        else:
            c.execute("SELECT * FROM users WHERE username LIKE ?", (uname,))
        return c.fetchone()
    except Exception as e:
        print(f"Error in get_user_by_username: {e}")
        return None
    finally:
        release_connection(conn)

# ================== USER ==================

def register_user(uid, username, full_name=None, last_command=None, referred_by=None):
    """
    Upserts a user into the database and tracks activity.
    Increments total_actions and updates last_active_at/last_command.
    """
    conn = get_connection()
    try:
        c = conn.cursor()
        now = get_eth_now()
        is_new = False
        
        # PostgreSQL Logic
        if DATABASE_URL:
            c.execute("SELECT id FROM users WHERE id=%s", (uid,))
            if not c.fetchone():
                c.execute("""
                    INSERT INTO users (id, username, full_name, joined_at, last_active_at, last_command, total_actions, referred_by) 
                    VALUES (%s, %s, %s, %s, %s, %s, 1, %s)
                """, (uid, username, full_name, now, now, last_command, referred_by))
                is_new = True
            else:
                c.execute("""
                    UPDATE users SET 
                        username=%s, 
                        full_name=%s, 
                        last_active_at=%s, 
                        last_command=%s, 
                        total_actions = total_actions + 1 
                    WHERE id=%s
                """, (username, full_name, now, last_command, uid))
        # SQLite Logic
        else:
            c.execute("SELECT id FROM users WHERE id=?", (uid,))
            if not c.fetchone():
                c.execute("""
                    INSERT INTO users (id, username, full_name, joined_at, last_active_at, last_command, total_actions, referred_by) 
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """, (uid, username, full_name, now, now, last_command, referred_by))
                is_new = True
            else:
                c.execute("""
                    UPDATE users SET 
                        username=?, 
                        full_name=?, 
                        last_active_at=?, 
                        last_command=?, 
                        total_actions = total_actions + 1 
                    WHERE id=?
                """, (username, full_name, now, last_command, uid))
        conn.commit()
        return is_new
    except Exception as e:
        print(f"Error in register_user: {e}")
        return False
    finally:
        release_connection(conn)

def get_user_details(uid):
    """Retrieves full details for a specific user, including referral count."""
    conn = get_connection()
    try:
        c = conn.cursor()
        query = """
            SELECT 
                u.id, u.username, u.full_name, u.lang, u.joined_at, 
                u.last_active_at, u.last_command, u.total_actions, 
                u.referred_by, u.is_blocked,
                (SELECT COUNT(*) FROM users WHERE referred_by = u.id) as referral_count 
            FROM users u 
            WHERE u.id = %s
        """ if DATABASE_URL else """
            SELECT 
                u.id, u.username, u.full_name, u.lang, u.joined_at, 
                u.last_active_at, u.last_command, u.total_actions, 
                u.referred_by, u.is_blocked,
                (SELECT (SELECT COUNT(*) FROM users WHERE referred_by = u.id)) as referral_count 
            FROM users u 
            WHERE u.id = ?
        """
        c.execute(query, (uid,))
        return c.fetchone()
    except Exception as e:
        print(f"Error in get_user_details: {e}")
        return None
    finally:
        release_connection(conn)

def get_lang(uid):
    """Retrieves user's preferred language, defaulting to English."""
    conn = get_connection()
    try:
        c = conn.cursor()
        if DATABASE_URL:
            c.execute("SELECT lang FROM users WHERE id=%s", (uid,))
        else:
            c.execute("SELECT lang FROM users WHERE id=?", (uid,))
        row = c.fetchone()
        return row[0] if row and row[0] else "en"
    except Exception as e:
        print(f"Error in get_lang: {e}")
        return "en"
    finally:
        release_connection(conn)

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
    """Registers or updates group information."""
    conn = get_connection()
    try:
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
    except Exception as e:
        print(f"Error in register_group: {e}")
    finally:
        release_connection(conn)

def get_all_group_ids():
    """Returns a list of all unique group IDs."""
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT id FROM groups")
        rows = c.fetchall()
        return [r[0] for r in rows]
    except Exception as e:
        print(f"Error in get_all_group_ids: {e}")
        return []
    finally:
        release_connection(conn)

def get_all_groups(limit=10, offset=0):
    """Retrieves all groups with their titles and join dates."""
    conn = get_connection()
    try:
        c = conn.cursor()
        query = "SELECT id, title, joined_at, is_blocked FROM groups ORDER BY joined_at DESC "
        params = []
        if limit is not None:
            query += " LIMIT %s" if DATABASE_URL else " LIMIT ?"
            params.append(limit)
        if offset is not None:
            query += " OFFSET %s" if DATABASE_URL else " OFFSET ?"
            params.append(offset)
            
        c.execute(query, tuple(params))
        return c.fetchall()
    except Exception as e:
        print(f"Error in get_all_groups: {e}")
        return []
    finally:
        release_connection(conn)

def get_group_count(query=None):
    """Returns total number of groups, supporting optional search query."""
    conn = get_connection()
    try:
        c = conn.cursor()
        if query:
            stmt = "SELECT COUNT(*) FROM groups WHERE title ILIKE %s OR id::text LIKE %s" if DATABASE_URL else "SELECT COUNT(*) FROM groups WHERE title LIKE ? OR CAST(id AS TEXT) LIKE ?"
            search_param = f"%{query}%"
            c.execute(stmt, (search_param, search_param))
        else:
            c.execute("SELECT COUNT(*) FROM groups")
        return c.fetchone()[0]
    except Exception as e:
        print(f"Error in get_group_count: {e}")
        return 0
    finally:
        release_connection(conn)

def search_groups(query, limit=10, offset=0):
    """Searches for groups by title or ID."""
    conn = get_connection()
    try:
        c = conn.cursor()
        search_param = f"%{query}%"
        stmt = "SELECT id, title, joined_at, is_blocked FROM groups WHERE title ILIKE %s OR id::text LIKE %s ORDER BY joined_at DESC " if DATABASE_URL else "SELECT id, title, joined_at, is_blocked FROM groups WHERE title LIKE ? OR CAST(id AS TEXT) LIKE ? ORDER BY joined_at DESC "
        
        if limit is not None:
            stmt += " LIMIT %s" if DATABASE_URL else " LIMIT ?"
        if offset is not None:
            stmt += " OFFSET %s" if DATABASE_URL else " OFFSET ?"
            
        params = (search_param, search_param)
        if limit is not None: params += (limit,)
        if offset is not None: params += (offset,)
            
        c.execute(stmt, params)
        return c.fetchall()
    except Exception as e:
        print(f"Error searching groups: {e}")
        return []
    finally:
        release_connection(conn)

def block_entity_db(entity_id, is_user=True):
    """Blocks a user or group."""
    conn = get_connection()
    try:
        c = conn.cursor()
        table = "users" if is_user else "groups"
        stmt = f"UPDATE {table} SET is_blocked = TRUE WHERE id = %s" if DATABASE_URL else f"UPDATE {table} SET is_blocked = 1 WHERE id = ?"
        c.execute(stmt, (entity_id,))
        conn.commit()
    except Exception as e:
        print(f"Error blocking entity {entity_id}: {e}")
    finally:
        release_connection(conn)

def unblock_entity_db(entity_id, is_user=True):
    """Unblocks a user or group."""
    conn = get_connection()
    try:
        c = conn.cursor()
        table = "users" if is_user else "groups"
        stmt = f"UPDATE {table} SET is_blocked = FALSE WHERE id = %s" if DATABASE_URL else f"UPDATE {table} SET is_blocked = 0 WHERE id = ?"
        c.execute(stmt, (entity_id,))
        conn.commit()
    except Exception as e:
        print(f"Error unblocking entity {entity_id}: {e}")
    finally:
        release_connection(conn)

def is_blocked_db(entity_id):
    """Checks if a user or group is blocked."""
    conn = get_connection()
    try:
        c = conn.cursor()
        # Check users first
        c.execute("SELECT is_blocked FROM users WHERE id = %s" if DATABASE_URL else "SELECT is_blocked FROM users WHERE id = ?", (entity_id,))
        row = c.fetchone()
        if row and row[0]:
            return True
        
        # Check groups
        c.execute("SELECT is_blocked FROM groups WHERE id = %s" if DATABASE_URL else "SELECT is_blocked FROM groups WHERE id = ?", (entity_id,))
        row = c.fetchone()
        return bool(row and row[0])
    except Exception as e:
        print(f"Error checking block status for {entity_id}: {e}")
        return False
    finally:
        release_connection(conn)

# ================== API KEYS ==================

def get_or_create_api_key(uid):
    """Retrieves the user's existing API key or creates a new one."""
    conn = get_connection()
    try:
        c = conn.cursor()
        if DATABASE_URL:
            c.execute("SELECT api_key FROM api_keys WHERE uid = %s", (uid,))
        else:
            c.execute("SELECT api_key FROM api_keys WHERE uid = ?", (uid,))
        
        row = c.fetchone()
        if row:
            return row[0]
            
        # Create a new key
        new_key = "ec_" + secrets.token_hex(16)
        
        if DATABASE_URL:
            c.execute(
                "INSERT INTO api_keys (uid, api_key) VALUES (%s, %s)",
                (uid, new_key)
            )
        else:
            c.execute(
                "INSERT INTO api_keys (uid, api_key) VALUES (?, ?)",
                (uid, new_key)
            )
        conn.commit()
        return new_key
    except Exception as e:
        print(f"Error in get_or_create_api_key: {e}")
        return None
    finally:
        release_connection(conn)

def verify_and_track_api_key(api_key):
    """Verifies an API key and increments its request count if valid. Returns uid if valid, None otherwise."""
    conn = get_connection()
    try:
        c = conn.cursor()
        if DATABASE_URL:
            c.execute("SELECT uid FROM api_keys WHERE api_key = %s", (api_key,))
            row = c.fetchone()
            if row:
                uid = row[0]
                c.execute("UPDATE api_keys SET requests_count = requests_count + 1 WHERE uid = %s", (uid,))
                conn.commit()
                return uid
        else:
            c.execute("SELECT uid FROM api_keys WHERE api_key = ?", (api_key,))
            row = c.fetchone()
            if row:
                uid = row[0]
                c.execute("UPDATE api_keys SET requests_count = requests_count + 1 WHERE uid = ?", (uid,))
                conn.commit()
                return uid
        return None
    except Exception as e:
        print(f"Error tracking API key: {e}")
        return None
    finally:
        release_connection(conn)
