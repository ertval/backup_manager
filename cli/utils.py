import os
from cli.config import BACKUPS_DIR, SCHEDULES_FILE, LOGS_DIR, LOG_FILE

def init():
    """Create all required folders and files if they don't exist."""
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        if not os.path.exists(LOG_FILE):
            open(LOG_FILE, "w").close()
        if not os.path.exists(SCHEDULES_FILE):
            open(SCHEDULES_FILE, "w").close()
    except Exception as e:
        print(f"Warning: could not initialize required files/folders: {e}")

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
