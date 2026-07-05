import os
import signal
import subprocess
import sys
from cli.config import PID_FILE, SERVICE_LOG_FILE
from cli.logger import log


def _read_pid():
    try:
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return None

def _is_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

def start_service():
    pid = _read_pid()
    if pid and _is_running(pid):
        print("Error: backup_service already running.")
        log("Error: backup_service already running")
        log("Error: backup_service already running", log_file=SERVICE_LOG_FILE)
        return

    try:
        service_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backup_service.py")
        proc = subprocess.Popen(
            [sys.executable, service_path],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
        os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
        with open(PID_FILE, "w") as f:
            f.write(str(proc.pid))
        print("backup_service started.")
        log("backup_service started")
    except Exception as e:
        print("Error: can't start backup_service.")
        log(f"Error: can't start backup_service: {e}")

def stop_service():
    pid = _read_pid()
    if not pid or not _is_running(pid):
        print("Error: can't stop backup_service.")
        log("Error: can't stop backup_service")
        return

    try:
        os.kill(pid, signal.SIGTERM)
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        print("backup_service stopped.")
        log("backup_service stopped")
        log("Service stopped", log_file=SERVICE_LOG_FILE)
    except Exception as e:
        print("Error: can't stop backup_service.")
        log(f"Error: can't stop backup_service: {e}")
