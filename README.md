# Backup Manager

A lightweight, robust, and zero-dependency backup scheduling utility for Unix/Linux environments. 

Backup Manager is written in pure Python 3 and features a Command Line Interface (CLI) orchestration script (`backup_manager.py`) paired with a lightweight background daemon process (`backup_service.py`) that monitors and executes scheduled folder/file compression.

---

## Features

- **CLI-based Schedule Management**: Create, list, and delete backup tasks quickly.
- **Background Daemon Service**: Automate daily backups running safely in the background.
- **Robust Process Tracking**: Process state is safely tracked using PID locking (`backup_service.pid`), preventing duplicate daemon instances.
- **Zero Third-Party Dependencies**: Built entirely using Python standard libraries (`subprocess`, `shlex`, `tarfile`, `signal`).
- **Comprehensive Logging**: Detailed, timestamped logs for CLI interactions and background process runs.

---

## Directory Structure

Upon first execution, the manager initializes its directory components:

```
backup_manager/
├── docs/
│   ├── audit.md              # Functional audit steps
│   └── requirements.md       # Product requirements documentation
├── AGENTS.md                 # Agent coding conventions and rules
├── backup_manager.py         # CLI orchestration script (User Interface)
├── backup_service.py         # Daemon process (Scheduling & execution engine)
├── backup_schedules.txt      # Plaintext schedules database
├── logs/
│   ├── backup_manager.log    # CLI diagnostic log
│   ├── backup_service.log    # Daemon diagnostic log
│   └── backup_service.pid    # Running daemon lock file (stores active PID)
└── backups/
    └── *.tar                 # Target backup tar archives
```

---

## CLI Usage Reference

Manage your backups using the `backup_manager.py` command:

```bash
python3 ./backup_manager.py <command> [argument]
```

### Supported Commands

| Command | Argument | Description |
|:---|:---|:---|
| `start` | None | Spawns `backup_service.py` in the background (using an isolated session) if not already running. |
| `stop` | None | Gracefully kills the active background daemon via PID tracking and cleans up states. |
| `create` | `"path_to_save;hh:mm;backup_name"` | Adds a new backup task. Throws error if input does not match formatting. |
| `list` | None | Prints all active backup schedules with a zero-based index. |
| `delete` | `[index]` | Removes the backup schedule at the specified index. |
| `backups` | None | Lists all generated backup archives in the `./backups` folder. |

---

## Examples & Walkthroughs

### 1. Creating Backup Schedules
Schedule folder backups by providing a semicolon-delimited string specifying `path_to_save`, `trigger_time (24-hour HH:MM)`, and `output_name`:

```bash
$ python3 ./backup_manager.py create "testing;18:21;backup_test"
$ python3 ./backup_manager.py create "testing2;13:11;passed_time_backup"
```

### 2. Listing Schedules
Review all configured backup parameters:

```bash
$ python3 ./backup_manager.py list
0: testing;18:21;backup_test
1: testing2;13:11;passed_time_backup
```

### 3. Deleting Schedules
Remove an existing configuration line using its index number. Remaining indexes automatically re-align:

```bash
$ python3 ./backup_manager.py delete 1
$ python3 ./backup_manager.py list
0: testing;18:21;backup_test
```

### 4. Running and Stopping the Daemon
Launch the daemon in the background to start processing triggers.

```bash
$ python3 ./backup_manager.py start
```

To stop the daemon process:

```bash
$ python3 ./backup_manager.py stop
```

### 5. Reviewing Log Audits
Verify actions and error outputs in the dedicated log folders:

**CLI logs (`./logs/backup_manager.log`):**
```text
[03/07/2026 18:21] New schedule added: testing;18:21;backup_test
[03/07/2026 18:21] Error: malformed schedule: wrong_format
[03/07/2026 18:21] backup_service started
```

**Daemon logs (`./logs/backup_service.log`):**
```text
[03/07/2026 18:21] Backup done for testing in backups/backup_test.tar
[03/07/2026 18:22] Error: folder not found for path_to_save: missing_folder
```

---

## System Architecture Details

### 1. Process Communication & PID Files
The daemon engine tracks lifecycle safety via `logs/backup_service.pid`. 
- When `backup_manager.py start` is invoked, it checks if a process with the PID recorded inside `backup_service.pid` is active. If so, duplicate startup is blocked.
- When `backup_manager.py stop` is called, it sends a `SIGTERM` signal to the target PID, waits for graceful exit, and cleans up the file.

### 2. Schedule Loop
The background daemon parses `backup_schedules.txt` every cycle. At the end of each iteration, the service sleeps for **45 seconds**. 

To prevent duplicate triggers during the 60-second window when the target minute matches, the daemon tracks completed job states internally and ensures only a single `.tar` archive is compiled for any matching schedule on a given calendar day.

### 3. Archive Safety
Backups are archived as standard `.tar` files. To verify integrity manual extraction or inspections can be performed:

```bash
tar -tvf ./backups/backup_test.tar
```

---

## Diagnostics & Troubleshooting

- **Service Fails to Stop**: If the service does not stop using the CLI, check `./logs/backup_service.pid` for the running process ID and verify with `ps -p <PID>`. You can terminate it manually using `kill -15 <PID>` and remove the PID file.
- **Permissions Error**: Ensure scripts have execute rights:
  ```bash
  chmod +x backup_manager.py backup_service.py
  ```
- **Passed Schedules**: If a schedule's time has already passed for the current day, it will not trigger until the schedule matches the target time on the following day.
