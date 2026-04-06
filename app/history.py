import json
import os

FILE = "data/history.json"


def _load():
    if not os.path.exists(FILE):
        return {}
    with open(FILE, "r") as f:
        return json.load(f)


def _save(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)


def save_history(user_id, entry):
    data = _load()
    uid = str(user_id)

    if uid not in data:
        data[uid] = []

    data[uid].append(entry)
    _save(data)


def get_history(user_id):
    data = _load()
    return data.get(str(user_id), [])
