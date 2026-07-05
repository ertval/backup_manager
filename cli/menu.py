import sys
from cli.logger import log
from cli.utils import init, clear
from cli.backup import create_backup, list_backups
from cli.schedule import create_schedule, list_schedules, delete_schedule
from cli.service import start_service, stop_service

def show_menu():
    print("=== Backup Manager ===")
    print("1. Create Backup")
    print("2. Create Schedule")
    print("3. List Schedules")
    print("4. Delete Schedule")
    print("5. List Backups")
    print("6. Start Daemon")
    print("7. Stop Daemon")
    print("8. Exit")
    print("======================")

def main():
    init()
    log("CLI started")

    clear()
    print("Welcome to Backup Manager!")
    print("Your personal backup scheduling tool.")

    while True:
        print()
        show_menu()
        choice = input("Select an option: ").strip()
        clear()

        if choice == "1":
            create_backup()
        elif choice == "2":
            create_schedule()
        elif choice == "3":
            list_schedules()
        elif choice == "4":
            delete_schedule()
        elif choice == "5":
            list_backups()
        elif choice == "6":
            start_service()
        elif choice == "7":
            stop_service()
        elif choice == "8":
            log("CLI exited")
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid option, try again.")
            log(f"Invalid menu option selected: '{choice}'")
