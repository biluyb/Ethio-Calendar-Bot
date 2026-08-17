from .base import get_connection, release_connection, get_eth_now, DATABASE_URL

def is_admin_db(uid):
    conn = get_connection()
    try:
        c = conn.cursor()
        if DATABASE_URL:
            c.execute("SELECT id FROM admins WHERE id=%s", (uid,))
        else:
            c.execute("SELECT id FROM admins WHERE id=?", (uid,))
        res = c.fetchone()
        return True if res else False
    finally:
        release_connection(conn)

def get_admins_db():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT id FROM admins")
        rows = c.fetchall()
        return [r[0] for r in rows]
    finally:
        release_connection(conn)

def add_admin_db(uid):
    conn = get_connection()
    try:
        c = conn.cursor()
        now = get_eth_now()
        if DATABASE_URL:
            c.execute("INSERT INTO admins (id, added_at) VALUES (%s, %s) ON CONFLICT DO NOTHING", (uid, now))
        else:
            c.execute("INSERT INTO admins (id, added_at) VALUES (?, ?)", (uid, now))
        conn.commit()
    except Exception:
        pass # Already exists
    finally:
        release_connection(conn)

def remove_admin_db(uid):
    conn = get_connection()
    try:
        c = conn.cursor()
        if DATABASE_URL:
            c.execute("DELETE FROM admins WHERE id=%s", (uid,))
        else:
            c.execute("DELETE FROM admins WHERE id=?", (uid,))
        conn.commit()
    finally:
        release_connection(conn)

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
            
        params = [search_param, search_param]
        if limit is not None: params.append(limit)
        if offset is not None: params.append(offset)
            
        c.execute(stmt, tuple(params))
        return c.fetchall()
    except Exception as e:
        print(f"Error searching groups: {e}")
        return []
    finally:
        release_connection(conn)

def _block_tables(entity_id, is_user):
    """Returns the table(s) an entity belongs to for block operations.

    Negative IDs are group chat IDs (modern supergroups are -100xxx...);
    positive IDs are users (or legacy groups, handled when is_user=False).
    """
    if entity_id < 0:
        return ["groups"]
    return ["users"] if is_user else ["groups"]


def _set_blocked(entity_id, tables, blocked):
    """Upserts is_blocked for the given entity across the given tables.

    An upsert (not a plain UPDATE) is required so that IDs not yet present in
    the database — e.g. a user who never interacted with the bot — are still
    blocked. A plain UPDATE on a missing row silently affects 0 rows, leaving
    the entity unblocked and making /block trivially bypassable.
    """
    conn = get_connection()
    try:
        c = conn.cursor()
        pg_val = "TRUE" if blocked else "FALSE"
        sq_val = 1 if blocked else 0
        for table in tables:
            if DATABASE_URL:
                if table == "users":
                    c.execute(
                        "INSERT INTO users (id, is_blocked, joined_at, last_active_at) "
                        f"VALUES (%s, {pg_val}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
                        f"ON CONFLICT (id) DO UPDATE SET is_blocked = {pg_val}",
                        (entity_id,),
                    )
                else:
                    c.execute(
                        "INSERT INTO groups (id, is_blocked, joined_at) "
                        f"VALUES (%s, {pg_val}, CURRENT_TIMESTAMP) "
                        f"ON CONFLICT (id) DO UPDATE SET is_blocked = {pg_val}",
                        (entity_id,),
                    )
            else:
                if table == "users":
                    c.execute(
                        "INSERT INTO users (id, is_blocked, joined_at, last_active_at) "
                        f"VALUES (?, {sq_val}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
                        "ON CONFLICT(id) DO UPDATE SET is_blocked = excluded.is_blocked",
                        (entity_id,),
                    )
                else:
                    c.execute(
                        "INSERT INTO groups (id, is_blocked, joined_at) "
                        f"VALUES (?, {sq_val}, CURRENT_TIMESTAMP) "
                        "ON CONFLICT(id) DO UPDATE SET is_blocked = excluded.is_blocked",
                        (entity_id,),
                    )
        conn.commit()
    except Exception as e:
        print(f"Error setting block status for {entity_id}: {e}")
    finally:
        release_connection(conn)


def block_entity_db(entity_id, is_user=True):
    """Blocks a user or group."""
    _set_blocked(entity_id, _block_tables(entity_id, is_user), blocked=True)

def unblock_entity_db(entity_id, is_user=True):
    """Unblocks a user or group."""
    _set_blocked(entity_id, _block_tables(entity_id, is_user), blocked=False)

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
