from .base import get_connection, release_connection, get_eth_now, DATABASE_URL

def is_admin_db(uid):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT id FROM admins WHERE id=%s" if DATABASE_URL else "SELECT id FROM admins WHERE id=?", (uid,))
        return bool(c.fetchone())
    finally:
        release_connection(conn)

def get_admins_db():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT id FROM admins")
        return [r[0] for r in c.fetchall()]
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
    except Exception: pass
    finally:
        release_connection(conn)

def remove_admin_db(uid):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM admins WHERE id=%s" if DATABASE_URL else "DELETE FROM admins WHERE id=?", (uid,))
        conn.commit()
    finally:
        release_connection(conn)

def register_group(group_id, title):
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
    finally:
        release_connection(conn)

def get_all_groups(limit=10, offset=0):
    conn = get_connection()
    try:
        c = conn.cursor()
        query = "SELECT id, title, joined_at, is_blocked FROM groups ORDER BY joined_at DESC"
        params = []
        if limit: query += " LIMIT %s" if DATABASE_URL else " LIMIT ?"; params.append(limit)
        if offset: query += " OFFSET %s" if DATABASE_URL else " OFFSET ?"; params.append(offset)
        c.execute(query, tuple(params))
        return c.fetchall()
    finally:
        release_connection(conn)

def get_group_count(query=None):
    conn = get_connection()
    try:
        c = conn.cursor()
        if query:
            stmt = "SELECT COUNT(*) FROM groups WHERE title ILIKE %s OR id::text LIKE %s" if DATABASE_URL else "SELECT COUNT(*) FROM groups WHERE title LIKE ? OR CAST(id AS TEXT) LIKE ?"
            c.execute(stmt, (f"%{query}%", f"%{query}%"))
        else:
            c.execute("SELECT COUNT(*) FROM groups")
        return c.fetchone()[0]
    finally:
        release_connection(conn)

def block_entity_db(entity_id, is_user=True):
    conn = get_connection()
    try:
        c = conn.cursor()
        table = "users" if is_user else "groups"
        c.execute(f"UPDATE {table} SET is_blocked = {'TRUE' if DATABASE_URL else '1'} WHERE id = %s" if DATABASE_URL else f"UPDATE {table} SET is_blocked = {'TRUE' if DATABASE_URL else '1'} WHERE id = ?", (entity_id,))
        conn.commit()
    finally:
        release_connection(conn)

def unblock_entity_db(entity_id, is_user=True):
    conn = get_connection()
    try:
        c = conn.cursor()
        table = "users" if is_user else "groups"
        c.execute(f"UPDATE {table} SET is_blocked = {'FALSE' if DATABASE_URL else '0'} WHERE id = %s" if DATABASE_URL else f"UPDATE {table} SET is_blocked = {'FALSE' if DATABASE_URL else '0'} WHERE id = ?", (entity_id,))
        conn.commit()
    finally:
        release_connection(conn)

def is_blocked_db(entity_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT is_blocked FROM users WHERE id = %s" if DATABASE_URL else "SELECT is_blocked FROM users WHERE id = ?", (entity_id,))
        row = c.fetchone()
        if row and row[0]: return True
        c.execute("SELECT is_blocked FROM groups WHERE id = %s" if DATABASE_URL else "SELECT is_blocked FROM groups WHERE id = ?", (entity_id,))
        row = c.fetchone()
        return bool(row and row[0])
    finally:
        release_connection(conn)

def get_all_group_ids():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT id FROM groups")
        return [r[0] for r in c.fetchall()]
    finally:
        release_connection(conn)
