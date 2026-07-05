import sys
from cli.menu import main
from cli.utils import init, parse_time, is_valid_name, is_safe_path
from cli.logger import log
from cli.schedule import add_schedule, remove_schedule, list_schedules
from cli.backup import list_backups
from cli.service import start_service, stop_service

def cmd_create(schedule_str):
    parts = schedule_str.strip().split(";")
    if len(parts) != 3 or not parts[0] or not parts[2]:
        print(f"Error: malformed schedule: {schedule_str}")
        log(f"Error: malformed schedule: {schedule_str}")
        return

    path, time_str, name = parts

    if not is_safe_path(path):
        print(f"Error: malformed schedule: {schedule_str}")
        log(f"Error: malformed schedule: {schedule_str}")
        return

    if not is_valid_name(name):
        print(f"Error: malformed schedule: {schedule_str}")
        log(f"Error: malformed schedule: {schedule_str}")
        return

    parsed = parse_time(time_str)
    if parsed is None:
        print(f"Error: malformed schedule: {schedule_str}")
        log(f"Error: malformed schedule: {schedule_str}")
        return

    hh, mm = parsed
    add_schedule(f"{path};{hh}:{mm};{name}")

def cmd_delete(index_str):
    if not index_str.isdigit():
        print(f"Error: can't find schedule at index {index_str}")
        log(f"Error: can't find schedule at index {index_str}")
        return
    remove_schedule(int(index_str))

if __name__ == "__main__":
    init()

    try:
        if len(sys.argv) == 1:
            main()
            sys.exit(0)

        command = sys.argv[1].lower()

        if command == "create":
            if len(sys.argv) < 3:
                print("Usage: backup_manager.py create \"path;hh:mm;name\"")
                log("Error: malformed schedule: (no argument provided)")
            else:
                cmd_create(sys.argv[2])

        elif command == "list":
            list_schedules()

        elif command == "delete":
            if len(sys.argv) < 3:
                print("Usage: backup_manager.py delete [index]")
                log("Error: can't find schedule at index (none provided)")
            else:
                cmd_delete(sys.argv[2])

        elif command == "backups":
            list_backups()

        elif command == "start":
            start_service()

        elif command == "stop":
            stop_service()

        else:
            print("Error: unknown instruction")
            log("Error: unknown instruction")
    except Exception as e:
        print(f"Error: unexpected CLI failure: {e}")
        log(f"Error: unexpected CLI failure: {e}")
