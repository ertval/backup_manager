import os
import re
from cli.config import LOGS_DIR, LOG_FILE

SAFE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')

def is_valid_name(name):
    return bool(SAFE_NAME_PATTERN.match(name))

def is_safe_path(path):
    parts = os.path.normpath(path).split(os.sep)
    return '..' not in parts

def init():
    """Create only the logs folder and log file so logging always works."""
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        if not os.path.exists(LOG_FILE):
            open(LOG_FILE, "w").close()
    except Exception as e:
        print(f"Warning: could not initialize logs: {e}")

def clear():
    os.system("clear")

def parse_time(raw):
    raw = raw.strip()

    if ":" in raw:
        parts = raw.split(":", 1)
    elif " " in raw:
        parts = raw.split(None, 1)
    else:
        parts = [raw]

    try:
        hh = int(parts[0])
        mm = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        return None

    if not (0 <= hh <= 23) or not (0 <= mm <= 59):
        return None

    return (f"{hh:02d}", f"{mm:02d}")
