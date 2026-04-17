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
    finally:
        release_connection(conn)

def set_lang(uid, lang):
    conn = get_connection()
    try:
        c = conn.cursor()
        if DATABASE_URL:
            c.execute("UPDATE users SET lang=%s WHERE id=%s", (lang, uid))
        else:
            c.execute("UPDATE users SET lang=? WHERE id=?", (lang, uid))
        conn.commit()
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
    finally:
        release_connection(conn)

def get_all_users(sort_by="last_active_at", order="DESC", limit=None, offset=None):
    """Retrieves all users with optional filtering for blocked status and dynamic ordering."""
    conn = get_connection()
    try:
        c = conn.cursor()
        order = "ASC" if order.upper() == "ASC" else "DESC"
        field = "last_active_at"
        if sort_by == "joined_at": field = "joined_at"
        elif sort_by == "referrals": field = "referral_count"
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
    finally:
        release_connection(conn)

def search_users(query, sort_by="last_active_at", order="DESC", limit=None, offset=None):
    """Searches users with support for blocked filtering, sorting, and dynamic ordering."""
    conn = get_connection()
    try:
        c = conn.cursor()
        q = f"%{query}%"
        order = "ASC" if order.upper() == "ASC" else "DESC"
        field = "last_active_at"
        if sort_by == "joined_at": field = "joined_at"
        elif sort_by == "referrals": field = "referral_count"
        order_clause = f"{field} {order}"
        filter_blocked = (sort_by == "blocked")
        where_conds = []
        if filter_blocked:
            where_conds.append("u.is_blocked = TRUE" if DATABASE_URL else "u.is_blocked = 1")
        search_part = f"(u.username {'ILIKE' if DATABASE_URL else 'LIKE'} %s OR CAST(u.id AS TEXT) LIKE %s)" if DATABASE_URL else "(u.username LIKE ? OR CAST(u.id AS TEXT) LIKE ?)"
        where_conds.append(search_part)
        where_clause = "WHERE " + " AND ".join(where_conds)
        base_query = f"SELECT u.*, (SELECT COUNT(*) FROM users WHERE referred_by = u.id) as referral_count FROM users u {where_clause}"
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
    finally:
        release_connection(conn)

def get_top_referrers(limit=10, offset=0):
    conn = get_connection()
    try:
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
        return c.fetchall()
    finally:
        release_connection(conn)

def get_referrers_count():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(DISTINCT referred_by) FROM users WHERE referred_by IS NOT NULL")
        res = c.fetchone()
        return res[0] if res else 0
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
    finally:
        release_connection(conn)
