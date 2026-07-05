import os
from cli.config import SERVICE_LOG_FILE, BACKUPS_DIR
from cli.logger import log
from cli.backup import do_backup

def create_backup(path, name):
    """Create backup from path. Returns True on success, False on failure."""
    if name != os.path.basename(name) or name in (".", ".."):
        log("Error: rejected unsafe backup name", SERVICE_LOG_FILE)
        return False

    if not os.path.exists(path):
        log(f"Error: folder not found for path: {path}", SERVICE_LOG_FILE)
        return False

    try:
        do_backup(path, name, log_file=SERVICE_LOG_FILE)
        tar_path = os.path.join(BACKUPS_DIR, f"{name}.tar")
        return os.path.exists(tar_path)
    except Exception as e:
        log(f"Error: failed to create backup for '{path}': {e}", SERVICE_LOG_FILE)
        return False
