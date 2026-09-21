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
    """Logs a single admin action. Ignores viewing activity logs to avoid clutter."""
    if action and ("/admin_activity" in action or action == "admin_activity"):
        return
    if detail and "Viewed activity log" in detail:
        return
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


def get_admin_activity(admin_id=None, limit: int = 15, offset: int = 0):
    """Fetches paginated admin activity logs sorted by recent date. Excludes view logs clutter."""
    conn = get_connection()
    try:
        c = conn.cursor()
        where_clauses = [
            "action NOT LIKE '%admin_activity%'",
            "(detail IS NULL OR detail NOT LIKE '%Viewed activity log%')"
        ]
        params = []

        if admin_id and str(admin_id) not in ["0", "all", "None"]:
            where_clauses.append("admin_id = %s" if DATABASE_URL else "admin_id = ?")
            params.append(int(admin_id))

        where_sql = " WHERE " + " AND ".join(where_clauses)
        query = f"SELECT id, admin_id, action, detail, target_id, performed_at FROM admin_activity{where_sql} ORDER BY performed_at DESC, id DESC "
        query += "LIMIT %s OFFSET %s" if DATABASE_URL else "LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        c.execute(query, tuple(params))
        return c.fetchall()
    except Exception as e:
        print(f"Error fetching admin activity: {e}")
        return []
    finally:
        release_connection(conn)


def get_admin_activity_count(admin_id=None) -> int:
    """Returns total count of logged admin activities (excluding view logs)."""
    conn = get_connection()
    try:
        c = conn.cursor()
        where_clauses = [
            "action NOT LIKE '%admin_activity%'",
            "(detail IS NULL OR detail NOT LIKE '%Viewed activity log%')"
        ]
        params = []

        if admin_id and str(admin_id) not in ["0", "all", "None"]:
            where_clauses.append("admin_id = %s" if DATABASE_URL else "admin_id = ?")
            params.append(int(admin_id))

        where_sql = " WHERE " + " AND ".join(where_clauses)
        query = f"SELECT COUNT(*) FROM admin_activity{where_sql}"

        c.execute(query, tuple(params))
        return c.fetchone()[0]
    except Exception as e:
        print(f"Error counting admin activity: {e}")
        return 0
    finally:
        release_connection(conn)


def get_admin_activity_summary():
    """Returns summary of activity per admin sorted by most recent activity date."""
    conn = get_connection()
    try:
        c = conn.cursor()
        query = """
            SELECT admin_id, COUNT(*) as total_actions,
                   MAX(performed_at) as last_action
            FROM admin_activity
            WHERE action NOT LIKE '%admin_activity%' AND (detail IS NULL OR detail NOT LIKE '%Viewed activity log%')
            GROUP BY admin_id
            ORDER BY last_action DESC
        """
        c.execute(query)
        return c.fetchall()
    except Exception as e:
        print(f"Error getting activity summary: {e}")
        return []
    finally:
        release_connection(conn)
