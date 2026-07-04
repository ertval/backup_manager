import sys
import os
from cli.menu import main
from cli.utils import init, parse_time
from cli.logger import log
from cli.schedule import add_schedule, remove_schedule, list_schedules
from cli.backup import list_backups

def cmd_create(schedule_str):
    parts = schedule_str.strip().split(";")
    if len(parts) != 3 or not parts[0] or not parts[2]:
        print(f"Error: malformed schedule: {schedule_str}")
        log(f"Error: malformed schedule: {schedule_str}")
        return

    path, time_str, name = parts

    if not os.path.exists(path):
        print(f"Error: malformed schedule: {schedule_str}")
        log(f"Error: malformed schedule: {schedule_str} (path '{path}' does not exist)")
        return

    parsed = parse_time(time_str)
    if parsed is None:
        print(f"Error: malformed schedule: {schedule_str}")
        log(f"Error: malformed schedule: {schedule_str} (invalid time '{time_str}')")
        return

    hh, mm = parsed
    add_schedule(f"{path};{hh}:{mm};{name}")

def cmd_delete(index_str):
    if not index_str.isdigit():
        print(f"Error: invalid index '{index_str}'")
        log(f"Error: invalid index '{index_str}'")
        return
    remove_schedule(int(index_str))

if __name__ == "__main__":
    init()

    if len(sys.argv) == 1:
        main()
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "create":
        if len(sys.argv) < 3:
            print("Usage: backup_manager.py create \"path;hh:mm;name\"")
            log("Error: create command missing argument")
        else:
            cmd_create(sys.argv[2])

    elif command == "list":
        list_schedules()

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: backup_manager.py delete [index]")
            log("Error: delete command missing index")
        else:
            cmd_delete(sys.argv[2])

    elif command == "backups":
        list_backups()

    elif command == "start":
        print("Start: not yet implemented.")

    elif command == "stop":
        print("Stop: not yet implemented.")

    else:
        print("Error: unknown instruction")
        log(f"Error: unknown instruction '{sys.argv[1]}'")
