import json
import os
import random
from datetime import date, timedelta

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "physics_history.json")

def get_today_in_history() -> dict | None:
    try:
        with open(HISTORY_FILE) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    except (FileNotFoundError, json.JSONDecodeError):
        return None

    today = date.today()
    # Walk back day by day until we hit a date that has an entry (max one year)
    for days_back in range(366):
        day = today - timedelta(days=days_back)
        events = data.get(day.strftime("%m-%d"))
        if events:
            event = dict(random.choice(events))
            event["date"] = f"{day.strftime('%B')} {day.day}"   # e.g. "October 4"
            event["exact"] = days_back == 0
            return event
    return None