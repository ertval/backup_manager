import os
import tarfile
from datetime import datetime
from cli.config import BACKUPS_DIR
from cli.logger import log
from cli.utils import is_valid_name, is_safe_path

# --- Core logic ---

def do_backup(path, name):
    try:
        if not is_valid_name(name):
            print(f"Error: invalid backup name '{name}'. Only letters, numbers, underscores and dashes are allowed.")
            log(f"Error: invalid backup name '{name}' (path traversal attempt blocked)")
            return

        folder_name = os.path.basename(os.path.normpath(path))
        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M")
        full_name = f"{name}_{timestamp}"

        os.makedirs(BACKUPS_DIR, exist_ok=True)
        tar_path = os.path.join(BACKUPS_DIR, f"{full_name}.tar")

        if os.path.exists(tar_path):
            print(f"Error: backup '{full_name}.tar' already exists.")
            log(f"Error: backup '{full_name}.tar' already exists, skipping")
            return

        with tarfile.open(tar_path, "w") as tar:
            tar.add(path, arcname=folder_name)
        print(f"Backup created: {tar_path}")
        log(f"Backup done for {path} in backups/{full_name}.tar")
    except Exception as e:
        print(f"Error creating backup: {e}")
        log(f"Error: folder not found for path: {path}")

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

    do_backup(path, name)

def list_backups():
    try:
        if not os.path.exists(BACKUPS_DIR):
            print("Error: can't find backups directory.")
            log("Error: can't find backups directory")
            return

        files = [f for f in os.listdir(BACKUPS_DIR) if f.endswith(".tar")]

        if not files:
            print("No backups found.")
            log("Show backups list")
            return

        print("\n--- Backups ---")
        for f in files:
            print(f)

        log("Show backups list")

    except Exception as e:
        print(f"Error: can't find backups directory.")
        log("Error: can't find backups directory")
