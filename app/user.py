import json
import os

FILE = "data/users.json"


def _load():
    if not os.path.exists(FILE):
        return {}
    with open(FILE, "r") as f:
        return json.load(f)


def _save(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)


# -----------------------
# USER MANAGEMENT
# -----------------------

def register_user(user_id):
    data = _load()

    if str(user_id) not in data:
        data[str(user_id)] = {
            "lang": "en"
        }
        _save(data)


def set_lang(user_id, lang):
    data = _load()
    uid = str(user_id)

    if uid not in data:
        data[uid] = {}

    data[uid]["lang"] = lang
    _save(data)


def get_lang(user_id):
    data = _load()
    return data.get(str(user_id), {}).get("lang", "en")

