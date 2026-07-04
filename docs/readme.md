# Backup Manager

## Overview

Backup Manager is a Python-based backup system that schedules and performs automated backups from the command line. The system allows users to create, list, and delete backup schedules, control a background service, and generate compressed `.tar` backup files. It solves the problem of automating local directory backups with proper logging and error handling.

## Role-play

You have been hired as junior DevOps engineers at a small company. The team currently performs manual backups of important directories, which is error-prone and time-consuming. Your manager has asked you to build an automated backup system that runs in the background, follows a schedule, and logs every action. Your mission is to deliver two Python scripts that work together to manage and execute scheduled backups reliably.

## Learning Objectives

Through this project, you will learn to:

- Implement scheduled file operations using Python
- Design a command-line interface that manages a background service
- Build file compression and archiving using the `tarfile` library
- Analyze process management techniques using `subprocess` and `os` modules
- Implement structured logging and error handling with `try` and `except` blocks

## Instructions

You will create two scripts that manage and perform scheduled backups.

### Part 1: `backup_manager.py`

The script `backup_manager.py` orchestrates the backup service and manages the file `backup_schedules.txt`. It accepts the following command-line arguments:

#### `create [schedule]`

Add a new backup schedule to `backup_schedules.txt`.

- Schedule format: `path_to_save;HH:MM;backup_name`
- **Log examples:**
  - `[dd/mm/yyyy hh:mm] New schedule added: test2;16:07;office_docs`
  - `[dd/mm/yyyy hh:mm] Error: malformed schedule: test;`

#### `list`

Print the scheduled backups from `backup_schedules.txt`, with an index before each entry.

- **Log examples:**
  - `[dd/mm/yyyy hh:mm] Show schedules list`
  - `[dd/mm/yyyy hh:mm] Error: can't find backup_schedules.txt`

#### `delete [index]`

Delete the backup schedule at the given index (starting at 0) from `backup_schedules.txt`.

- **Log examples:**
  - `[dd/mm/yyyy hh:mm] Schedule at index 3 deleted`
  - `[dd/mm/yyyy hh:mm] Error: can't find schedule at index 3`
  - `[dd/mm/yyyy hh:mm] Error: can't find backup_schedules.txt`

#### `start`

Run `backup_service.py` in the background.

- **Log examples:**
  - `[dd/mm/yyyy hh:mm] backup_service started`
  - `[dd/mm/yyyy hh:mm] Error: backup_service already running`

#### `stop`

Kill the `backup_service.py` process.

- **Log examples:**
  - `[dd/mm/yyyy hh:mm] backup_service stopped`
  - `[dd/mm/yyyy hh:mm] Error: can't stop backup_service`

#### `backups`

List the backup files in `./backups`.

- **Log examples:**
  - `[dd/mm/yyyy hh:mm] Show backups list`
  - `[dd/mm/yyyy hh:mm] Error: can't find backups directory`

All actions and errors from `backup_manager.py` are logged to `./logs/backup_manager.log`.

### Part 2: `backup_service.py`

The script `backup_service.py` checks the schedules in `backup_schedules.txt` and performs backups at the scheduled times.

- The service runs in an infinite loop.
- During each iteration, the service checks the backup schedules.
- The service performs a backup when the current hour and minute match a scheduled time.
- Schedules whose time has already passed are removed from `backup_schedules.txt` after processing.
- Backups are saved as compressed `.tar` files in `./backups`.
- All actions and errors from `backup_service.py` are logged to `./logs/backup_service.log`.

At the end of each loop iteration, make the service sleep for about 45 seconds to save processor cycles.

### Part 3: Logging and Error Handling

- All scripts must use `try` and `except` blocks to handle errors.
- All actions and errors are logged to the appropriate file in the `./logs` directory.
- `backup_manager.py` logs to `./logs/backup_manager.log`.
- `backup_service.py` logs to `./logs/backup_service.log`.
- Each log entry must start with a timestamp in the format `[dd/mm/yyyy hh:mm]`.
- Unknown or invalid commands must produce an appropriate error log entry.

## Usage

Here is an example showing how the backup system works (assuming the script runs at 16:07):

```bash
echo "--> Create 3 new schedules"
python3 ./backup_manager.py create "test;16:07;backup_test"
python3 ./backup_manager.py create "test1;16:07;personal_data"
python3 ./backup_manager.py create "test2;16:07;office_docs"
echo "--> Try to add a malformed schedule"
python3 ./backup_manager.py create "test;"
echo "--> Instruction list"
python3 ./backup_manager.py list
python3 ./backup_manager.py start
python3 ./backup_manager.py stop
echo "--> Instruction backups"
python3 ./backup_manager.py backups
echo "--> Content of the directory"
ls
echo "--> cat on ./logs/backup_manager.log"
cat ./logs/backup_manager.log
echo "--> cat on ./logs/backup_service.log"
cat ./logs/backup_service.log
echo "--> Content of ./backups"
ls ./backups
```

The output should be similar to:

```
--> Create 3 new schedules
--> Try to add a malformed schedule
--> Instruction list
0: test;16:07;backup_test
1: test1;16:07;personal_data
2: test2;16:07;office_docs
--> Instruction backups
personal_data.tar
office_docs.tar
backup_test.tar
--> Content of the directory
backup_manager.py  backups  backup_schedules.txt  backup_service.py  logs
--> cat on ./logs/backup_manager.log
[dd/mm/yyyy 16:07] New schedule added: test;16:07;backup_test
[dd/mm/yyyy 16:07] New schedule added: test1;16:07;personal_data
[dd/mm/yyyy 16:07] New schedule added: test2;16:07;office_docs
[dd/mm/yyyy 16:07] Error: malformed schedule: test;
[dd/mm/yyyy 16:07] Show schedules list
[dd/mm/yyyy 16:07] backup_service started
[dd/mm/yyyy 16:07] backup_service stopped
[dd/mm/yyyy 16:07] Show backups list
--> cat on ./logs/backup_service.log
[dd/mm/yyyy 16:07] Backup done for test in backups/backup_test.tar
[dd/mm/yyyy 16:07] Backup done for test1 in backups/personal_data.tar
[dd/mm/yyyy 16:07] Backup done for test2 in backups/office_docs.tar
--> Content of ./backups
backup_test.tar  office_docs.tar  personal_data.tar
```

## Submission Structure

```
backup-manager/
├── backup_manager.py              # CLI script for managing schedules and service
├── backup_service.py              # Background service that performs scheduled backups
├── logs/                          # Directory for log files (created at runtime)
│   ├── backup_manager.log         # Logs from backup_manager.py
│   └── backup_service.log         # Logs from backup_service.py
├── backups/                       # Directory for backup .tar files (created at runtime)
├── backup_schedules.txt           # Schedule file (created at runtime)
└── README.md                      # Project documentation
```

## Tips

- Use `subprocess.Popen` with the flag `start_new_session=True` to run the backup service in the background.
- Use `os.kill` to stop a process by finding its process ID.
- Use `ps -A -f` to inspect active processes and their arguments during debugging.
- The standard library `tarfile` is very useful for creating `.tar` archives programmatically.
- Keep your code modular by creating single-task functions for each command.

## Resources

- [Error handling in Python](https://docs.python.org/3/tutorial/errors.html): Official tutorial on `try` and `except` blocks.
- [Spawn a subprocess in Python](https://docs.python.org/3/library/subprocess.html): Documentation for running and managing background processes.
- [Simple lexical analysis, shlex](https://docs.python.org/3/library/shlex.html): Useful for safely parsing shell-like command strings.
- [Reading and writing files](https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files): Official guide for file I/O operations.
- [Set handlers for asynchronous events, signal](https://docs.python.org/3/library/signal.html): Documentation for handling process signals.
- [Try and Except](https://realpython.com/python-exceptions/): Beginner-friendly guide to Python exception handling.
- [tarfile module](https://docs.python.org/3/library/tarfile.html): Official documentation for creating and extracting `.tar` archives.

## AI Prompts For Learning

- *"Explain how to manage background processes in Python using the subprocess module, including how to start, monitor, and kill a child process from a parent script."*
- *"Describe how to design a command-line tool in Python that reads a schedule file, performs time-based actions, and logs all operations and errors to a file."*
