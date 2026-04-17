import secrets
from .base import get_connection, release_connection, DATABASE_URL

def get_or_create_api_key(uid):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT api_key FROM api_keys WHERE uid = %s" if DATABASE_URL else "SELECT api_key FROM api_keys WHERE uid = ?", (uid,))
        row = c.fetchone()
        if row: return row[0]
        new_key = "ec_" + secrets.token_hex(16)
        c.execute("INSERT INTO api_keys (uid, api_key) VALUES (%s, %s)" if DATABASE_URL else "INSERT INTO api_keys (uid, api_key) VALUES (?, ?)", (uid, new_key))
        conn.commit()
        return new_key
    finally:
        release_connection(conn)

def verify_and_track_api_key(api_key):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT uid FROM api_keys WHERE api_key = %s" if DATABASE_URL else "SELECT uid FROM api_keys WHERE api_key = ?", (api_key,))
        row = c.fetchone()
        if row:
            uid = row[0]
            c.execute("UPDATE api_keys SET requests_count = requests_count + 1 WHERE uid = %s" if DATABASE_URL else "UPDATE api_keys SET requests_count = requests_count + 1 WHERE uid = ?", (uid,))
            conn.commit()
            return uid
        return None
    finally:
        release_connection(conn)

def get_api_usage_stats(limit=10, offset=0):
    conn = get_connection()
    try:
        c = conn.cursor()
        sql = """
            SELECT u.id, u.username, u.full_name, ak.api_key, ak.requests_count, ak.created_at
            FROM api_keys ak
            JOIN users u ON ak.uid = u.id
            ORDER BY ak.requests_count DESC
            LIMIT %s OFFSET %s
        """ if DATABASE_URL else """
            SELECT u.id, u.username, u.full_name, ak.api_key, ak.requests_count, ak.created_at
            FROM api_keys ak
            JOIN users u ON ak.uid = u.id
            ORDER BY ak.requests_count DESC
            LIMIT ? OFFSET ?
        """
        c.execute(sql, (limit, offset))
        return c.fetchall()
    finally:
        release_connection(conn)

def get_total_api_users():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM api_keys")
        res = c.fetchone()
        return res[0] if res else 0
    finally:
        release_connection(conn)

def revoke_api_key_db(uid):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM api_keys WHERE uid = %s" if DATABASE_URL else "DELETE FROM api_keys WHERE uid = ?", (uid,))
        conn.commit()
        return True
    finally:
        release_connection(conn)
