import os
from cli.config import SCHEDULES_FILE, SERVICE_LOG_FILE
from cli.logger import log

def read_schedules():
    """Return the raw, non-empty lines of backup_schedules.txt, or None if it can't be read."""
    try:
        with open(SCHEDULES_FILE, "r") as f:
            return [l.rstrip("\n") for l in f.readlines() if l.strip()]
    except Exception:
        log("Error: cannot open backup_schedules", SERVICE_LOG_FILE)
        return None

def parse_schedule(line):
    """Parse 'path;hh:mm;name' into (path, hh, mm, name), or None if malformed."""
    parts = line.split(";")
    if len(parts) != 3:
        return None

    path, time_str, name = (p.strip() for p in parts)
    if not path or not name or ":" not in time_str:
        return None

    # `name` becomes a filename under ./backups/ — reject anything that could
    # escape that directory (e.g. "../../etc/cron.d/evil").
    if name in (".", "..") or name != os.path.basename(name):
        return None

    hh_str, mm_str = time_str.split(":", 1)
    try:
        hh = int(hh_str)
        mm = int(mm_str)
    except ValueError:
        return None

    if not (0 <= hh <= 23) or not (0 <= mm <= 59):
        return None

    return (path, hh, mm, name)
