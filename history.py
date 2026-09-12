import json
import os
import random
from datetime import date

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "physics_history.json")

def get_today_in_history() -> dict | None:
    try:
        with open(HISTORY_FILE) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    key = date.today().strftime("%m-%d")
    events = data.get(key)
    if not events:
        return None
    return random.choice(events)