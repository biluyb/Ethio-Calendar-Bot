import sqlite3

DB = "bot.db"

# ================== INIT ==================



def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()


    # ✅ CREATE NEW TABLE (correct structure)
    c.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        text TEXT
    )
    """)

    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM users")
    rows = c.fetchall()

    conn.close()
    return rows

def search_users(query):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username LIKE ? OR id LIKE ?", (f"%{query}%", f"%{query}%"))
    rows = c.fetchall()

    conn.close()
    return rows

# ================== USER ==================

def register_user(uid, username):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT id FROM users WHERE id=?", (uid,))
    if not c.fetchone():
        c.execute("INSERT INTO users (id, username) VALUES (?, ?)", (uid, username))

    conn.commit()
    conn.close()

def get_lang(uid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT lang FROM users WHERE id=?", (uid,))
    row = c.fetchone()

    conn.close()
    return row[0] if row else "en"

def set_lang(uid, lang):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("UPDATE users SET lang=? WHERE id=?", (lang, uid))

    conn.commit()
    conn.close()

# ================== HISTORY ==================

def save_history(uid, text):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("INSERT INTO history (username, text) VALUES (?, ?)", (uid, text))

    conn.commit()
    conn.close()

def get_history(user):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT text FROM history WHERE username=?", (user,))
    data = [x[0] for x in c.fetchall()]
    conn.close()
    return data
    
def get_user(update):
    user = update.effective_user
    return user.username or user.first_name or str(user.id)
