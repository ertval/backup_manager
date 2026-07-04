import os
import signal
from cli.config import PID_FILE

def register_pid():
    """Write this process's PID to the PID file."""
    try:
        os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        return True
    except Exception:
        return False

def unregister_pid():
    """Remove the PID file, if present."""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return True
    except Exception:
        return False

def handle_shutdown_signal(signum, frame):
    unregister_pid()
    raise SystemExit(0)

def install_signal_handlers():
    """Clean up the PID file on both a `kill`/SIGTERM and Ctrl-C/SIGINT."""
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)
