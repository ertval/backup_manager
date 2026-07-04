import os
import tarfile
from datetime import datetime
from cli.config import BACKUPS_DIR
from cli.logger import log

# --- Core logic (used by both interactive menu and argument mode) ---

def do_backup(path, name):
    """Create a .tar backup of path, saved as name_timestamp.tar in backups/."""
    try:
        folder_name = os.path.basename(os.path.normpath(path))
        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M")
        full_name = f"{name}_{timestamp}"

        tar_path = os.path.join(BACKUPS_DIR, f"{full_name}.tar")
        with tarfile.open(tar_path, "w") as tar:
            tar.add(path, arcname=folder_name)
        print(f"Backup created: {tar_path}")
        log(f"Backup created: {tar_path} (source: '{path}')")
    except Exception as e:
        print(f"Error creating backup: {e}")
        log(f"Create Backup - Error: failed to create backup for '{path}': {e}")

# --- Interactive menu functions ---

def create_backup():
    path = input("Enter the path of the folder to back up (folder name): ").strip()

    if not path:
        print("Error: path cannot be empty.")
        log("Create Backup - Error: path cannot be empty")
        return

    if not os.path.exists(path):
        print(f"Error: path '{path}' does not exist.")
        log(f"Create Backup - Error: path '{path}' does not exist")
        return

    name = input("Enter a name for the backup: ").strip()

    if not name:
        print("Error: name cannot be empty.")
        log(f"Create Backup - Error: name cannot be empty (path was '{path}')")
        return

    do_backup(path, name)

def list_backups():
    try:
        files = [f for f in os.listdir(BACKUPS_DIR) if f.endswith(".tar")]

        if not files:
            print("No backups found.")
            log("List Backups - no backups found")
            return

        print("\n--- Backups ---")
        for f in files:
            print(f)

        log("Show backups list")

    except Exception as e:
        print(f"Error reading backups: {e}")
        log(f"List Backups - Error: {e}")
