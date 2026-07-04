import os
import tarfile
from cli.config import BACKUPS_DIR, SERVICE_LOG_FILE
from cli.logger import log

def create_backup(path, name):
    """Create ./backups/{name}.tar from path. Returns True on success."""
    if not os.path.exists(path):
        log(f"Error: can't find path '{path}' for backup '{name}'", SERVICE_LOG_FILE)
        return False

    try:
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        tar_path = os.path.join(BACKUPS_DIR, f"{name}.tar")
        arcname = os.path.basename(os.path.normpath(path))
        with tarfile.open(tar_path, "w") as tar:
            tar.add(path, arcname=arcname)
        log(f"Backup done for {path} in backups/{name}.tar", SERVICE_LOG_FILE)
        return True
    except Exception as e:
        log(f"Error: failed to create backup for '{path}': {e}", SERVICE_LOG_FILE)
        return False
