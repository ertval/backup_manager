import os
from datetime import datetime
from cli.config import LOG_FILE

def log(message):
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    entry = f"[{timestamp}] {message}"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(entry + "\n")
    except Exception as e:
        print(f"Warning: could not write to log: {e}")
