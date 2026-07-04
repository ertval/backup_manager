import sys
from cli.logger import log
from cli.utils import init
from cli.backup import create_backup, list_backups
from cli.schedule import create_schedule, list_schedules, delete_schedule

def show_menu():
    print("\n=== Backup Manager ===")
    print("1. Create Backup")
    print("2. Create Schedule")
    print("3. List Schedules")
    print("4. Delete Schedule")
    print("5. List Backups")
    print("6. Exit")
    print("======================")

def main():
    init()
    log("CLI started")
    print("Welcome to Backup Manager!")
    print("Your personal backup scheduling tool.")

    while True:
        show_menu()
        choice = input("Select an option: ").strip()

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
            log("CLI exited")
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid option, try again.")
            log(f"Invalid menu option selected: '{choice}'")
