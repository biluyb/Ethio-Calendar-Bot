"""
Reminder System - Database Layer
Stores user date reminders and manages triggering status.
"""

from datetime import date
from .base import get_connection, release_connection, get_eth_now, DATABASE_URL
from app.utils import eth_to_greg, greg_to_eth


def init_reminder_table():
    """Creates the reminders table if it doesn't exist."""
    conn = get_connection()
    try:
        c = conn.cursor()
        if DATABASE_URL:
            c.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    eth_year INTEGER NOT NULL,
                    eth_month INTEGER NOT NULL,
                    eth_day INTEGER NOT NULL,
                    greg_date DATE NOT NULL,
                    message TEXT NOT NULL,
                    is_triggered BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_rem_user ON reminders(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_rem_greg ON reminders(greg_date, is_triggered)")
        else:
            c.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    eth_year INTEGER NOT NULL,
                    eth_month INTEGER NOT NULL,
                    eth_day INTEGER NOT NULL,
                    greg_date TEXT NOT NULL,
                    message TEXT NOT NULL,
                    is_triggered INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            try:
                c.execute("CREATE INDEX IF NOT EXISTS idx_rem_user ON reminders(user_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_rem_greg ON reminders(greg_date, is_triggered)")
            except Exception:
                pass
        conn.commit()
    except Exception as e:
        print(f"Error creating reminders table: {e}")
    finally:
        release_connection(conn)


def add_reminder(user_id: int, eth_year: int, eth_month: int, eth_day: int, message: str) -> int | None:
    """Adds a new reminder for an Ethiopian date."""
    conn = get_connection()
    try:
        # Convert Ethiopian date to Gregorian for exact target date matching
        gd, gm, gy = eth_to_greg(eth_day, eth_month, eth_year)
        greg_str = f"{gy:04d}-{gm:02d}-{gd:02d}"

        c = conn.cursor()
        if DATABASE_URL:
            c.execute("""
                INSERT INTO reminders (user_id, eth_year, eth_month, eth_day, greg_date, message)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (user_id, eth_year, eth_month, eth_day, greg_str, message[:500]))
            rem_id = c.fetchone()[0]
        else:
            c.execute("""
                INSERT INTO reminders (user_id, eth_year, eth_month, eth_day, greg_date, message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, eth_year, eth_month, eth_day, greg_str, message[:500]))
            rem_id = c.lastrowid

        conn.commit()
        return rem_id
    except Exception as e:
        print(f"Error adding reminder: {e}")
        return None
    finally:
        release_connection(conn)


def get_user_reminders(user_id: int, include_triggered: bool = False):
    """Retrieves all active reminders for a user."""
    conn = get_connection()
    try:
        c = conn.cursor()
        if DATABASE_URL:
            cond = "" if include_triggered else " AND is_triggered = FALSE"
            c.execute(f"SELECT id, eth_year, eth_month, eth_day, greg_date, message, is_triggered, created_at FROM reminders WHERE user_id = %s{cond} ORDER BY greg_date ASC", (user_id,))
        else:
            cond = "" if include_triggered else " AND is_triggered = 0"
            c.execute(f"SELECT id, eth_year, eth_month, eth_day, greg_date, message, is_triggered, created_at FROM reminders WHERE user_id = ?{cond} ORDER BY greg_date ASC", (user_id,))
        return c.fetchall()
    except Exception as e:
        print(f"Error fetching user reminders: {e}")
        return []
    finally:
        release_connection(conn)


def get_user_day_reminders(user_id: int, eth_year: int, eth_month: int, eth_day: int):
    """Retrieves reminders for a specific user and specific Ethiopian date."""
    conn = get_connection()
    try:
        c = conn.cursor()
        if DATABASE_URL:
            c.execute("SELECT id, message, is_triggered FROM reminders WHERE user_id = %s AND eth_year = %s AND eth_month = %s AND eth_day = %s", (user_id, eth_year, eth_month, eth_day))
        else:
            c.execute("SELECT id, message, is_triggered FROM reminders WHERE user_id = ? AND eth_year = ? AND eth_month = ? AND eth_day = ?", (user_id, eth_year, eth_month, eth_day))
        return c.fetchall()
    except Exception as e:
        print(f"Error fetching day reminders: {e}")
        return []
    finally:
        release_connection(conn)


def get_month_user_reminder_days(user_id: int, eth_year: int, eth_month: int) -> set:
    """Returns a set of eth_days in a month that have active user reminders."""
    conn = get_connection()
    try:
        c = conn.cursor()
        if DATABASE_URL:
            c.execute("SELECT DISTINCT eth_day FROM reminders WHERE user_id = %s AND eth_year = %s AND eth_month = %s AND is_triggered = FALSE", (user_id, eth_year, eth_month))
        else:
            c.execute("SELECT DISTINCT eth_day FROM reminders WHERE user_id = ? AND eth_year = ? AND eth_month = ? AND is_triggered = 0", (user_id, eth_year, eth_month))
        rows = c.fetchall()
        return {r[0] for r in rows}
    except Exception as e:
        print(f"Error fetching month reminder days: {e}")
        return set()
    finally:
        release_connection(conn)


def delete_reminder(reminder_id: int, user_id: int) -> bool:
    """Deletes a reminder owned by user_id."""
    conn = get_connection()
    try:
        c = conn.cursor()
        if DATABASE_URL:
            c.execute("DELETE FROM reminders WHERE id = %s AND user_id = %s", (reminder_id, user_id))
        else:
            c.execute("DELETE FROM reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting reminder: {e}")
        return False
    finally:
        release_connection(conn)


def get_due_reminders():
    """Fetches all non-triggered reminders whose greg_date <= today."""
    today_str = date.today().isoformat()
    conn = get_connection()
    try:
        c = conn.cursor()
        if DATABASE_URL:
            c.execute("SELECT id, user_id, eth_year, eth_month, eth_day, greg_date, message FROM reminders WHERE is_triggered = FALSE AND greg_date <= %s", (today_str,))
        else:
            c.execute("SELECT id, user_id, eth_year, eth_month, eth_day, greg_date, message FROM reminders WHERE is_triggered = 0 AND greg_date <= ?", (today_str,))
        return c.fetchall()
    except Exception as e:
        print(f"Error getting due reminders: {e}")
        return []
    finally:
        release_connection(conn)


def mark_reminder_triggered(reminder_id: int):
    """Marks a reminder as triggered."""
    conn = get_connection()
    try:
        c = conn.cursor()
        if DATABASE_URL:
            c.execute("UPDATE reminders SET is_triggered = TRUE WHERE id = %s", (reminder_id,))
        else:
            c.execute("UPDATE reminders SET is_triggered = 1 WHERE id = ?", (reminder_id,))
        conn.commit()
    except Exception as e:
        print(f"Error marking reminder triggered: {e}")
    finally:
        release_connection(conn)
