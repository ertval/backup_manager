import os
import tarfile
from datetime import datetime
from cli.config import BACKUPS_DIR, LOG_FILE
from cli.logger import log
from cli.utils import is_valid_name, is_safe_path

def _report(stdout_msg, log_msg=None, log_file=None):
    print(stdout_msg)
    if log_file is not None:
        log(log_msg or stdout_msg, log_file)
    else:
        log(log_msg or stdout_msg)



# --- Core logic ---

def do_backup(path, name, log_file=LOG_FILE, manual=False):
    try:
        if not is_valid_name(name):
            log(f"Error: invalid backup name '{name}' (path traversal attempt blocked)", log_file)
            return

        if not os.path.exists(path):
            log(f"Error: folder not found for path: {path}", log_file)
            return

        folder_name = os.path.basename(os.path.normpath(path))
        full_name = name

        os.makedirs(BACKUPS_DIR, exist_ok=True)
        try:
            os.chmod(BACKUPS_DIR, 0o700)
        except Exception:
            pass

        tar_path = os.path.join(BACKUPS_DIR, f"{full_name}.tar")

        def secure_filter(tarinfo):
            if tarinfo.issym() or tarinfo.islnk():
                return None
            tarinfo.uid = 0
            tarinfo.gid = 0
            tarinfo.uname = "root"
            tarinfo.gname = "root"
            return tarinfo

        with tarfile.open(tar_path, "w") as tar:
            tar.add(path, arcname=folder_name, filter=secure_filter)

        try:
            os.chmod(tar_path, 0o600)
        except Exception:
            pass

        if manual:
            _report(f"Backup created: {tar_path}", f"Manual backup done for {path} in backups/{full_name}.tar", log_file)
        else:
            _report(f"Backup created: {tar_path}", f"Backup done for {path} in backups/{full_name}.tar", log_file)
    except Exception as e:
        _report(f"Error creating backup: {e}", f"Error: failed to create backup for {path}: {e}", log_file)

# --- Interactive menu functions ---

def create_backup():
    path = input("Enter the path of the folder to back up (folder name): ").strip()

    if not path:
        print("Error: path cannot be empty.")
        return

    if not is_safe_path(path):
        print(f"Error: path '{path}' contains invalid traversal characters.")
        log(f"Error: path traversal attempt blocked for path: '{path}'")
        return

    if not os.path.exists(path):
        print(f"Error: path '{path}' does not exist.")
        log(f"Error: folder not found for path: {path}")
        return

    name = input("Enter a name for the backup: ").strip()

    if not name:
        print("Error: name cannot be empty.")
        return

    if not is_valid_name(name):
        print("Error: invalid name. Only letters, numbers, underscores and dashes are allowed.")
        log(f"Error: invalid backup name '{name}' (path traversal attempt blocked)")
        return

    do_backup(path, name, manual=True)

def list_backups():
    try:
        if not os.path.exists(BACKUPS_DIR):
            _report("Error: can't find backups directory.", "Error: can't find backups directory")
            return

        files = [f for f in os.listdir(BACKUPS_DIR) if f.endswith(".tar")]

        if not files:
            _report("No backups found.", "Show backups list")
            return

        print("\n--- Backups ---")
        for f in files:
            print(f)

        log("Show backups list")

    except Exception as e:
        _report("Error: can't find backups directory.", "Error: can't find backups directory")
