from .base import get_connection, release_connection, get_eth_now, DATABASE_URL

def register_user(uid, username, full_name=None, last_command=None, referred_by=None):
    conn = get_connection()
    try:
        c = conn.cursor()
        now = get_eth_now()
        is_new = False
        if DATABASE_URL:
            c.execute("SELECT id FROM users WHERE id=%s", (uid,))
            if not c.fetchone():
                c.execute("INSERT INTO users (id, username, full_name, joined_at, last_active_at, last_command, total_actions, referred_by) VALUES (%s, %s, %s, %s, %s, %s, 1, %s)", (uid, username, full_name, now, now, last_command, referred_by))
                is_new = True
            else:
                c.execute("UPDATE users SET username=%s, full_name=%s, last_active_at=%s, last_command=%s, total_actions = total_actions + 1 WHERE id=%s", (username, full_name, now, last_command, uid))
        else:
            c.execute("SELECT id FROM users WHERE id=?", (uid,))
            if not c.fetchone():
                c.execute("INSERT INTO users (id, username, full_name, joined_at, last_active_at, last_command, total_actions, referred_by) VALUES (?, ?, ?, ?, ?, ?, 1, ?)", (uid, username, full_name, now, now, last_command, referred_by))
                is_new = True
            else:
                c.execute("UPDATE users SET username=?, full_name=?, last_active_at=?, last_command=?, total_actions = total_actions + 1 WHERE id=?", (username, full_name, now, last_command, uid))
        conn.commit()
        return is_new
    finally:
        release_connection(conn)

def get_user_details(uid):
    conn = get_connection()
    try:
        c = conn.cursor()
        query = "SELECT u.*, (SELECT COUNT(*) FROM users WHERE referred_by = u.id) as referral_count FROM users u WHERE u.id = %s" if DATABASE_URL else "SELECT u.*, (SELECT COUNT(*) FROM users WHERE referred_by = u.id) as referral_count FROM users u WHERE u.id = ?"
        c.execute(query, (uid,))
        return c.fetchone()
    finally:
        release_connection(conn)

def get_lang(uid):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT lang FROM users WHERE id=%s" if DATABASE_URL else "SELECT lang FROM users WHERE id=?", (uid,))
        row = c.fetchone()
        return row[0] if row and row[0] else "en"
    finally:
        release_connection(conn)

def set_lang(uid, lang):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("UPDATE users SET lang=%s WHERE id=%s" if DATABASE_URL else "UPDATE users SET lang=? WHERE id=?", (lang, uid))
        conn.commit()
    finally:
        release_connection(conn)

def get_all_user_ids():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT id FROM users")
        return [r[0] for r in c.fetchall()]
    finally:
        release_connection(conn)

def get_user_count(search_query=None, filter_blocked=False):
    conn = get_connection()
    try:
        c = conn.cursor()
        where = []
        params = []
        if filter_blocked: where.append("is_blocked = TRUE" if DATABASE_URL else "is_blocked = 1")
        if search_query:
            q = f"%{search_query}%"
            where.append("(username ILIKE %s OR CAST(id AS TEXT) LIKE %s)" if DATABASE_URL else "(username LIKE ? OR CAST(id AS TEXT) LIKE ?)")
            params.extend([q, q])
        sql = "SELECT COUNT(*) FROM users" + (" WHERE " + " AND ".join(where) if where else "")
        c.execute(sql, tuple(params))
        return c.fetchone()[0]
    finally:
        release_connection(conn)

def get_all_users(sort_by="last_active_at", order="DESC", limit=None, offset=None):
    conn = get_connection()
    try:
        c = conn.cursor()
        order = "ASC" if order.upper() == "ASC" else "DESC"
        field = {"joined_at": "joined_at", "referrals": "referral_count"}.get(sort_by, "last_active_at")
        where = "WHERE u.is_blocked = TRUE" if sort_by == "blocked" and DATABASE_URL else ("WHERE u.is_blocked = 1" if sort_by == "blocked" else "")
        query = f"SELECT u.*, (SELECT COUNT(*) FROM users WHERE referred_by = u.id) as referral_count FROM users u {where} ORDER BY {field} {order}"
        params = []
        if limit: query += " LIMIT %s" if DATABASE_URL else " LIMIT ?"; params.append(limit)
        if offset: query += " OFFSET %s" if DATABASE_URL else " OFFSET ?"; params.append(offset)
        c.execute(query, tuple(params))
        return c.fetchall()
    finally:
        release_connection(conn)

def search_users(query, sort_by="last_active_at", order="DESC", limit=None, offset=None):
    conn = get_connection()
    try:
        c = conn.cursor()
        q = f"%{query}%"
        order = "ASC" if order.upper() == "ASC" else "DESC"
        field = {"joined_at": "joined_at", "referrals": "referral_count"}.get(sort_by, "last_active_at")
        where = ["u.is_blocked = TRUE" if sort_by == "blocked" and DATABASE_URL else ("u.is_blocked = 1" if sort_by == "blocked" else None)]
        where.append("(u.username ILIKE %s OR CAST(u.id AS TEXT) LIKE %s)" if DATABASE_URL else "(u.username LIKE ? OR CAST(u.id AS TEXT) LIKE ?)")
        where = "WHERE " + " AND ".join(filter(None, where))
        sql = f"SELECT u.*, (SELECT COUNT(*) FROM users WHERE referred_by = u.id) as referral_count FROM users u {where} ORDER BY {field} {order}"
        params = [q, q]
        if limit: sql += " LIMIT %s" if DATABASE_URL else " LIMIT ?"; params.append(limit)
        if offset: sql += " OFFSET %s" if DATABASE_URL else " OFFSET ?"; params.append(offset)
        c.execute(sql, tuple(params))
        return c.fetchall()
    finally:
        release_connection(conn)
