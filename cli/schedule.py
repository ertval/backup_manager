import os
from cli.config import SCHEDULES_FILE
from cli.logger import log
from cli.utils import parse_time

# --- Core logic (used by both interactive menu and argument mode) ---

def add_schedule(schedule_line):
    """Write a validated schedule line to the schedules file."""
    try:
        with open(SCHEDULES_FILE, "a") as f:
            f.write(schedule_line + "\n")
        print(f"Schedule saved: {schedule_line}")
        log(f"New schedule added: {schedule_line}")
    except Exception as e:
        print(f"Error saving schedule: {e}")
        log(f"Error: failed to save schedule '{schedule_line}': {e}")

def remove_schedule(index):
    """Remove the schedule at the given index and rewrite the file."""
    try:
        with open(SCHEDULES_FILE, "r") as f:
            lines = [l.rstrip("\n") for l in f.readlines() if l.strip()]
    except Exception as e:
        print("Error: can't find backup_schedules.txt")
        log("Error: can't find backup_schedules.txt")
        return False

    if index < 0 or index >= len(lines):
        print(f"Error: can't find schedule at index {index}")
        log(f"Error: can't find schedule at index {index}")
        return False

    deleted = lines.pop(index)
    try:
        with open(SCHEDULES_FILE, "w") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
        print(f"Schedule at index {index} deleted.")
        log(f"Schedule at index {index} deleted: {deleted}")
        return True
    except Exception as e:
        print(f"Error saving changes: {e}")
        log(f"Error: failed to write schedules file: {e}")
        return False

# --- Interactive menu functions ---

def create_schedule():
    print("\n--- Create Schedule ---")
    print("(type 'exit' to leave, 'back' to go to previous step)\n")

    step = 1
    path = ""
    name = ""

    while step <= 3:

        # Step 1: Path
        if step == 1:
            raw = input("Enter the path of the folder to back up (folder name): ").strip()
            if raw.lower() == "exit":
                print("Leaving schedule menu.")
                log("Create Schedule - User exited at path step")
                return
            if raw.lower() == "back":
                print("Already at the first step.")
                continue
            if not raw:
                print("Error: path cannot be empty.")
                log("Create Schedule - Error: path cannot be empty")
                continue
            if not os.path.exists(raw):
                print(f"Error: path '{raw}' does not exist.")
                log(f"Create Schedule - Error: path '{raw}' does not exist")
                continue
            path = raw
            step = 2

        # Step 2: Name
        elif step == 2:
            raw = input("Enter a name for the backup: ").strip()
            if raw.lower() == "exit":
                print("Leaving schedule menu.")
                log(f"Create Schedule - User exited at name step (path was '{path}')")
                return
            if raw.lower() == "back":
                step = 1
                continue
            if not raw:
                print("Error: name cannot be empty.")
                log(f"Create Schedule - Error: name cannot be empty (path was '{path}')")
                continue
            name = raw
            step = 3

        # Step 3: Time + confirmation
        elif step == 3:
            raw = input("Enter time (hh:mm  or  hh mm  or  hh): ").strip()
            if raw.lower() == "exit":
                print("Leaving schedule menu.")
                log(f"Create Schedule - User exited at time step (path: '{path}', name: '{name}')")
                return
            if raw.lower() == "back":
                step = 2
                continue

            parsed = parse_time(raw)
            if parsed is None:
                print("Error: invalid time. Hours must be 0-23, minutes 0-59.")
                log(f"Create Schedule - Error: invalid time input '{raw}' (path: '{path}', name: '{name}')")
                continue

            hh, mm = parsed
            schedule_line = f"{path};{hh}:{mm};{name}"

            print(f"\nSchedule to be created:")
            print(f"  Folder : {path}")
            print(f"  Name   : {name}")
            print(f"  Time   : {hh}:{mm}")
            print(f"  Entry  : {schedule_line}")

            confirm = input("\nConfirm? (y/yes to save, n/no to re-enter time): ").strip().lower()

            if confirm in ("y", "yes"):
                add_schedule(schedule_line)
                return
            elif confirm in ("n", "no", "back"):
                continue
            elif confirm == "exit":
                print("Leaving schedule menu.")
                log(f"Create Schedule - User exited at confirmation step (path: '{path}', name: '{name}')")
                return
            else:
                print("Please enter y/yes or n/no.")

def list_schedules():
    try:
        with open(SCHEDULES_FILE, "r") as f:
            lines = [l.rstrip("\n") for l in f.readlines() if l.strip()]

        if not lines:
            print("No schedules found.")
            log("List Schedules - file is empty")
            return

        print("\n--- Schedules ---")
        for i, line in enumerate(lines):
            print(f"{i}: {line}")

        log("Show schedules list")

    except Exception as e:
        print(f"Error reading schedules: {e}")
        log(f"List Schedules - Error: {e}")

def delete_schedule():
    print("\n--- Delete Schedule ---")
    print("(type 'exit' to leave)\n")

    try:
        with open(SCHEDULES_FILE, "r") as f:
            lines = [l.rstrip("\n") for l in f.readlines() if l.strip()]
    except Exception as e:
        print(f"Error reading schedules: {e}")
        log(f"Delete Schedule - Error reading schedules: {e}")
        return

    if not lines:
        print("No schedules found.")
        log("Delete Schedule - no schedules to delete")
        return

    print("Current schedules:")
    for i, line in enumerate(lines):
        print(f"  {i}: {line}")

    while True:
        raw = input("\nEnter the index of the schedule to delete: ").strip()

        if raw.lower() == "exit":
            print("Leaving delete menu.")
            log("Delete Schedule - User exited")
            return

        if not raw.isdigit():
            print("Error: please enter a valid number.")
            log(f"Delete Schedule - Error: invalid index input '{raw}'")
            continue

        index = int(raw)

        if index < 0 or index >= len(lines):
            print(f"Error: can't find schedule at index {index}.")
            log(f"Delete Schedule - Error: can't find schedule at index {index}")
            continue

        print(f"\nSchedule to be deleted:")
        print(f"  {index}: {lines[index]}")

        confirm = input("Are you sure? (y/yes to delete, n/no to cancel): ").strip().lower()

        if confirm in ("y", "yes"):
            remove_schedule(index)
            return
        elif confirm in ("n", "no"):
            print("Deletion cancelled.")
            return
        elif confirm == "exit":
            print("Leaving delete menu.")
            log("Delete Schedule - User exited at confirmation")
            return
        else:
            print("Please enter y/yes or n/no.")
