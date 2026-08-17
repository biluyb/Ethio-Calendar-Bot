"""
Admin Activity Tracking - Database Layer
Records every admin action (command, callback, broadcast, etc.)
"""
from .base import get_connection, release_connection, get_eth_now, DATABASE_URL


def init_activity_table():
    """Creates the admin_activity table if it doesn't exist."""
    conn = get_connection()
    try:
        c = conn.cursor()
        if DATABASE_URL:
            c.execute("""
                CREATE TABLE IF NOT EXISTS admin_activity (
                    id SERIAL PRIMARY KEY,
                    admin_id BIGINT NOT NULL,
                    action TEXT NOT NULL,
                    detail TEXT,
                    target_id BIGINT,
                    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_admin_act_admin ON admin_activity(admin_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_admin_act_time ON admin_activity(performed_at)")
        else:
            c.execute("""
                CREATE TABLE IF NOT EXISTS admin_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    detail TEXT,
                    target_id INTEGER,
                    performed_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            try:
                c.execute("CREATE INDEX IF NOT EXISTS idx_admin_act_admin ON admin_activity(admin_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_admin_act_time ON admin_activity(performed_at)")
            except Exception:
                pass
        conn.commit()
    except Exception as e:
        print(f"Error creating admin_activity table: {e}")
    finally:
        release_connection(conn)


def log_admin_action(admin_id: int, action: str, detail: str = None, target_id: int = None):
    """Logs a single admin action."""
    conn = get_connection()
    try:
        c = conn.cursor()
        now = get_eth_now()
        if DATABASE_URL:
            c.execute(
                "INSERT INTO admin_activity (admin_id, action, detail, target_id, performed_at) VALUES (%s, %s, %s, %s, %s)",
                (admin_id, action[:200], (detail or "")[:500], target_id, now)
            )
        else:
            c.execute(
                "INSERT INTO admin_activity (admin_id, action, detail, target_id, performed_at) VALUES (?, ?, ?, ?, ?)",
                (admin_id, action[:200], (detail or "")[:500], target_id, now)
            )
        conn.commit()
    except Exception as e:
        print(f"Error logging admin action: {e}")
    finally:
        release_connection(conn)


def get_admin_activity(admin_id: int = None, limit: int = 50, offset: int = 0):
    """Fetches paginated admin activity logs. If admin_id is None, returns all admins."""
    conn = get_connection()
    try:
        c = conn.cursor()
        if admin_id:
            if DATABASE_URL:
                c.execute(
                    "SELECT id, admin_id, action, detail, target_id, performed_at FROM admin_activity WHERE admin_id=%s ORDER BY performed_at DESC LIMIT %s OFFSET %s",
                    (admin_id, limit, offset)
                )
            else:
                c.execute(
                    "SELECT id, admin_id, action, detail, target_id, performed_at FROM admin_activity WHERE admin_id=? ORDER BY performed_at DESC LIMIT ? OFFSET ?",
                    (admin_id, limit, offset)
                )
        else:
            if DATABASE_URL:
                c.execute(
                    "SELECT id, admin_id, action, detail, target_id, performed_at FROM admin_activity ORDER BY performed_at DESC LIMIT %s OFFSET %s",
                    (limit, offset)
                )
            else:
                c.execute(
                    "SELECT id, admin_id, action, detail, target_id, performed_at FROM admin_activity ORDER BY performed_at DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
        return c.fetchall()
    except Exception as e:
        print(f"Error fetching admin activity: {e}")
        return []
    finally:
        release_connection(conn)


def get_admin_activity_count(admin_id: int = None) -> int:
    """Returns the total count of logged admin activities."""
    conn = get_connection()
    try:
        c = conn.cursor()
        if admin_id:
            if DATABASE_URL:
                c.execute("SELECT COUNT(*) FROM admin_activity WHERE admin_id=%s", (admin_id,))
            else:
                c.execute("SELECT COUNT(*) FROM admin_activity WHERE admin_id=?", (admin_id,))
        else:
            c.execute("SELECT COUNT(*) FROM admin_activity")
        return c.fetchone()[0]
    except Exception as e:
        print(f"Error counting admin activity: {e}")
        return 0
    finally:
        release_connection(conn)


def get_admin_activity_summary():
    """Returns a summary of activity per admin (for dashboard view)."""
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT admin_id, COUNT(*) as total_actions,
                   MAX(performed_at) as last_action
            FROM admin_activity
            GROUP BY admin_id
            ORDER BY total_actions DESC
        """)
        return c.fetchall()
    except Exception as e:
        print(f"Error getting activity summary: {e}")
        return []
    finally:
        release_connection(conn)
