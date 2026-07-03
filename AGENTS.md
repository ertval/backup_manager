# Workspace Agent Instructions & Guidelines (AGENTS.md)

This document contains rules, constraints, coding standards, and execution guidelines for AI agents and automated tools working on the **Backup Manager** codebase.

---

## 1. Core Mandates

1. **Pure Python Standard Library**:
   - Do **NOT** introduce external dependencies (e.g. `pip install schedule`, `cron`, etc.).
   - Use native libraries: `subprocess` (for starting/managing services), `signal` and `os` (for process control and signals), `tarfile` (for compression), `datetime` and `time` (for cron schedules and delays), and `shlex` (for parsing terminal parameters safely).
2. **Defensive Error Handling**:
   - Use comprehensive `try-except` blocks around all system-level operations (I/O, process spawning, process killing, file reading/writing).
   - Unhandled exceptions must **never** terminate the background service daemon. If an operation fails, log the specific error details and proceed to the next loop iteration.
3. **Structured Log Outputs**:
   - All events and exceptions must log to their respective files inside `./logs`:
     - CLI: `./logs/backup_manager.log`
     - Service: `./logs/backup_service.log`
   - Log entries must begin with a timestamp in the following format:
     `[dd/mm/yyyy hh:mm] Message`
     - Example: `[14/02/2023 15:07] Error: can't stop backup_service`
4. **State Persistence**:
   - Use `./logs/backup_service.pid` to record the active PID of the running `backup_service.py` process.
   - Clean up the PID file gracefully upon service stop or when a dead process is detected.
5. **Requirements & Audit Compliance**:
   - **CLI Core Functionality**: `backup_manager.py` must support `start`, `stop`, `create "[path];[hh:mm];[name]"`, `list`, `delete [index]`, and `backups`.
   - **Daemon Core Functionality**: `backup_service.py` must run in an infinite loop, sleep for 45 seconds at the end of each iteration, check `backup_schedules.txt`, compare current local time (hour/minute) with schedule times, and compress target folders to `./backups/{backup_name}.tar`.
   - **CLI Error & Logging Audits**:
     - Invalid command inputs must log `Error: unknown instruction`.
     - Malformed schedule formats must log `Error: malformed schedule: <string>`.
     - Deleting a non-existent index must log `Error: can't find schedule at index <index>`.
     - Deleting missing file `backup_schedules.txt` must log `Error: can't find backup_schedules.txt`.
     - Stopping a stopped daemon must log `Error: can't stop backup_service`.
     - Running `backups` when the backups directory is missing must log `Error: can't find backups directory`.
   - **Daemon Error & Logging Audits**:
     - Starting without a schedule file must log `Error: cannot open backup_schedules` to `./logs/backup_service.log`.
     - Missing target folders for backups must be logged and skipped gracefully without crashing the daemon.
   - **Execution & Double Launch Rules**:
     - Re-running `start` when the daemon is already running must log `Error: backup_service already running` and abort.
     - Scheduled times that have already passed must not trigger immediate backups upon daemon start.
     - Generated tarballs must be verified to contain non-empty, non-damaged files matching the original directory hierarchy.

---

## 2. File Architecture

Maintain the following structure strictly:
```
backup_manager/
├── .agents/
│   └── AGENTS.md             # Workspace agent instructions
├── docs/
│   ├── audit.md              # QA validation checklist
│   └── requirements.md       # Technical requirements spec
├── AGENTS.md                 # This file (Agent instructions)
├── backup_manager.py         # CLI orchestration script
├── backup_service.py         # Background service daemon
├── backup_schedules.txt      # Text-based schedules storage
├── logs/
│   ├── backup_manager.log    # CLI action & error logs
│   ├── backup_service.log    # Daemon execution & error logs
│   └── backup_service.pid    # Running daemon PID file (ephemeral)
└── backups/
    └── *.tar                 # Generated backup archives
```

---

## 3. Implementation Specifics

### A. CLI Commands (`backup_manager.py`)
Ensure command parsing matches:
- `start`: Run `backup_service.py` in the background with `start_new_session=True`. Log service status or check if already running via the PID file.
- `stop`: Terminate the daemon using `os.kill(pid, signal.SIGTERM)`. Clean up the PID file. Handle errors if the PID file exists but the process does not.
- `create "[path];[hh:mm];[name]"`: Verify the format is valid before appending. Check for missing elements or invalid time formats and log a malformed error.
- `list`: Load and output lines of `backup_schedules.txt` prefixed by their 0-based indices (e.g., `0: path;12:00;name`).
- `delete [index]`: Remove the corresponding line from `backup_schedules.txt`. Re-index shifts cleanly.
- `backups`: List all `.tar` files in `./backups`.

### B. Daemon Service (`backup_service.py`)
Ensure scheduling loop implements:
- **Service PID Registration**: Writes its own PID to `./logs/backup_service.pid` when starting.
- **Sleep Cycle**: Sleeps for **45 seconds** at the end of each iteration.
- **Deduplication**: Implement logic (e.g., matching on date) to ensure a scheduled backup triggers exactly *once* per day during its designated minute, rather than multiple times due to the 45-second polling interval.
- **Tar Archive Creation**:
  - Compress target files using Python `tarfile`.
  - Save as `./backups/{backup_name}.tar`.
  - Validate folder presence before archiving; log and skip if folder is missing.

---

## 4. Quality Assurance & Verification Workflow

Agents editing the codebase must run manual verification or write test scripts to satisfy the audit check criteria in [audit.md](file:///home/ertval/code/zone-modules/backup_manager/docs/audit.md):

1. **Initialize Clean State**:
   ```bash
   rm -dr logs backups backup_schedules.txt
   ```
2. **Validate CLI Schedule Adding**:
   ```bash
   python3 ./backup_manager.py create "testing;18:21;backup_test"
   ```
3. **Verify Invalid Formats**:
   ```bash
   python3 ./backup_manager.py create "wrong_format;"
   # Confirm Error logged to logs/backup_manager.log
   ```
4. **Daemon Launch & Process Isolation**:
   ```bash
   python3 ./backup_manager.py start
   # Confirm PID file exists and process is visible via `ps -ef | grep backup_service`
   ```
5. **Double Launch Prevention**:
   ```bash
   python3 ./backup_manager.py start
   # Confirm error logs: "Error: backup_service already running"
   ```
6. **Execution Verification**:
   - Check if backup triggers correctly at target time.
   - Test generated `.tar` file integrity using `tar -tvf backups/[name].tar` to ensure no zero-byte or corrupt archives are generated.
