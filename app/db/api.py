import secrets
from .base import get_connection, release_connection, DATABASE_URL

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

def get_api_usage_stats(limit=10, offset=0):
    """Retrieves API usage statistics joined with user info."""
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
    except Exception as e:
        print(f"Error fetching API stats: {e}")
        return []
    finally:
        release_connection(conn)

def get_total_api_users():
    """Returns the total number of users with API keys."""
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM api_keys")
        res = c.fetchone()
        return res[0] if res else 0
    except Exception as e:
        print(f"Error counting API users: {e}")
        return 0
    finally:
        release_connection(conn)

def revoke_api_key_db(uid):
    """Deletes an API key for a specific user."""
    conn = get_connection()
    try:
        c = conn.cursor()
        sql = "DELETE FROM api_keys WHERE uid = %s" if DATABASE_URL else "DELETE FROM api_keys WHERE uid = ?"
        c.execute(sql, (uid,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error revoking API key: {e}")
        return False
    finally:
        release_connection(conn)
