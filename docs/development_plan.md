# Development Plan: Backup Manager

This document provides a detailed plan, architecture specification, and role assignment for implementing the Backup Manager project. The project is a modular backup orchestration utility comprised of a command-line controller (`backup_manager.py`) and a background scheduling daemon (`backup_service.py`).

---

## 1. Project Overview & Architecture

The Backup Manager is designed to manage and execute daily folder/file backups in a Unix environment using Python. It consists of two components:
1. **Command Line Interface (CLI)**: `backup_manager.py` allows users to create schedules, delete schedules, list schedules, list generated backups, and start/stop the background daemon.
2. **Background Daemon Service**: `backup_service.py` runs continuously in the background, monitors schedules in `backup_schedules.txt`, and generates compressed tarballs (`.tar`) in the `./backups` folder when schedules trigger.

### High-Level Components

```mermaid
graph TD
    User([User CLI]) -->|runs| CLI[backup_manager.py]
    CLI -->|spawns / kills| Daemon[backup_service.py]
    CLI -->|reads/writes| Schedules[(backup_schedules.txt)]
    CLI -->|reads| BackupsDir[(./backups/)]
    CLI -->|writes| CliLog[(./logs/backup_manager.log)]
    
    Daemon -->|polls| Schedules
    Daemon -->|checks time & creates tarballs| BackupsDir
    Daemon -->|writes| ServiceLog[(./logs/backup_service.log)]
    Daemon -->|records active process ID| PidFile[(./logs/backup_service.pid)]
```

---

## 2. Technical Specifications & Shared Interfaces

### A. The Schedules File (`backup_schedules.txt`)
- **Format**: Flat text file where each line is a semicolon-separated string:
  `path_to_save;time(hh:mm);backup_name`
  - Example: `testing;18:21;backup_test`
- **Integrity Guidelines**:
  - The CLI script (`backup_manager.py`) writes and deletes lines in this file.
  - The Daemon script (`backup_service.py`) reads and rewrites this file on each cycle (removing passed schedules).
  - Empty or malformed lines should be ignored by the daemon and logged as errors by both components.

### B. Process Orchestration & Daemon Tracking (`backup_service.pid`)
- To ensure only a single instance of `backup_service.py` runs and that the CLI can reliably stop it, we use a process ID (PID) file: `./logs/backup_service.pid`.
- **Start Process Flow (`backup_manager.py start`)**:
  1. Check if `./logs/backup_service.pid` exists.
  2. If it exists, read the PID and check if a process with that PID is active and running `backup_service.py`. If active, log `Error: backup_service already running` and abort.
  3. If not running, spawn `backup_service.py` in a new session using `subprocess.Popen` with the flag `start_new_session=True` (or equivalent Unix process isolation).
  4. Write the new PID to `./logs/backup_service.pid`.
  5. Log `[dd/mm/yyyy hh:mm] backup_service started`.
- **Stop Process Flow (`backup_manager.py stop`)**:
  1. Check if `./logs/backup_service.pid` exists.
  2. If it does not exist or the process is not active, log `Error: can't stop backup_service` (or `backup_service not running`) and abort.
  3. Read the PID, send a termination signal (`signal.SIGTERM` / `os.kill(pid, 15)`), wait briefly, and check if it has stopped.
  4. Clean up (delete) `./logs/backup_service.pid`.
  5. Log `[dd/mm/yyyy hh:mm] backup_service stopped`.

### C. Preventing Duplicate Backup Execution
Because the daemon runs in a loop checking the schedule, and sleeps for **45 seconds** (which is less than a minute), a schedule matching the current hour and minute (e.g. `18:21`) could potentially trigger twice within the same minute.
- **Contract**: The daemon must track executed backups.
- **Solution**: The daemon maintains an in-memory record of backups run today (e.g., storing a composite key of `(date, schedule_index)`). Alternatively, it can track the last completed run timestamp for each index and ensure it does not run again if the current date is the same.

---

## 3. Team Structure & Task Assignment

We have three developers assigned to this workspace:

### **Developer 1 (User / PM / QA)**
* **Role**: Product Owner, QA Lead, Integration Engineer.
* **Spec references**: [`docs/audit.md`](docs/audit.md) (all questions), [`docs/requirements.md`](docs/requirements.md) Testing section.
* **Responsibilities**:
  1. **Interface Coordination**
     1a. Define `backup_schedules.txt` format (`path;hh:mm;name`).
     1b. Define PID file contract (`./logs/backup_service.pid`).
     1c. Define log format (`[dd/mm/yyyy hh:mm] Message`).
     1d. Arbitrate disputes between Dev 2 and Dev 3 on file interfaces.
  2. **Phase 3 — Integration Tests** (`tests/integration/test_cli_daemon.py`)
     2a. Test `start` spawns real `backup_service.py` process visible via `ps`.
     2b. Test `stop` terminates process and removes `backup_service.pid`.
     2c. Test double `start` blocked with `Error: backup_service already running`.
     2d. Test full flow: `create` → `start` → backup triggers → `backups` shows `.tar` → `stop`.
  3. **Phase 3 — E2E Audit Tests** (`tests/e2e/test_audit_compliance.py`)
     3a. Map every `docs/audit.md` question to a test method (see §6 audit-to-test mapping).
     3b. Test clean env: `rm -dr logs backups backup_schedules.txt`.
     3c. Tests for `create`/`list`/`delete`/`start`/`stop`/`backups` with outputs and re-indexing.
     3d. Test manual backup at matching time, verify `.tar` contents via `tarfile`.
     3e. Test passed-time schedule does not trigger.
     3f. Test `.zip` folder backup works same as `.tar`.
     3g. Test unknown instruction logs `Error: unknown instruction`.
     3h. Test all error messages from audit.md §Error handling appear in log files.
     3i. Test source code contains `try`/`except`.
  4. **Validation & Test Execution**
     4a. Run `python3 -m unittest discover -s tests/unit -v` — gate before phase 3.
     4b. Run full suite `python3 -m unittest discover -s tests -v`.
     4c. Execute manual steps from `docs/audit.md` as exploratory supplement.
  5. **Robustness Inspections**
     5a. Review Dev 2 code for `try`/`except` on I/O, process spawn/kill, file ops.
     5b. Review Dev 3 code for `try`/`except` on I/O, tar creation, PID ops.
     5c. Verify both scripts handle missing `./logs/`, `./backups/`, `backup_schedules.txt` gracefully.

### **Developer 2**
* **Role**: CLI Architect.
* **Spec references**: [`docs/requirements.md`](docs/requirements.md) §First script, §Logging, §Testing.
* **Deliverable**: `backup_manager.py` + `tests/unit/test_backup_manager.py`.
* **Implementation steps**:
  1. **`create "[path];hh:mm;name"`**
     1a. Parse string: split on `;` into exactly 3 parts.
     1b. Validate time: `HH` 00–23, `MM` 00–59.
     1c. Validate path and name non-empty.
     1d. If valid: append to `backup_schedules.txt`, log `New schedule added: <string>`.
     1e. If invalid: log `Error: malformed schedule: <string>`, do not write.
  2. **`list`**
     2a. Open `backup_schedules.txt`.
     2b. Print each line with 0-based index prefix (`0: path;12:00;name`).
     2c. If file missing: log `Error: can't find backup_schedules.txt`.
      2d. Log `Show schedules list` on success.
  3. **`delete [index]`**
     3a. Open `backup_schedules.txt`, read all lines.
     3b. Validate index is within range (0 to len-1).
     3c. Remove line at index, write remaining lines back (re-indexing shifts down).
     3d. If index out of range: log `Error: can't find schedule at index <index>`.
     3e. If file missing: log `Error: can't find backup_schedules.txt`.
     3f. On success: log `Schedule at index <index> deleted`.
  4. **`backups`**
     4a. List `.tar` files in `./backups/`.
     4b. If directory missing: log `Error: can't find backups directory`.
     4c. Log `Show backups list` on success.
  5. **`start`**
     5a. Read `./logs/backup_service.pid`, check if process exists and is running.
     5b. If running: log `Error: backup_service already running`, abort.
     5c. Spawn `backup_service.py` via `subprocess.Popen` with `start_new_session=True`.
     5d. Write PID to `./logs/backup_service.pid`.
     5e. Log `[dd/mm/yyyy hh:mm] backup_service started`.
     5f. On failure: log `Error: can't start backup_service`.
   6. **`stop`**
      6a. Read `./logs/backup_service.pid`.
       6b. If missing or process dead: log `Error: can't stop backup_service` (canonical per `docs/requirements.md`). Note: `Error: backup_service not running` appears only in requirements §start examples, but audit.md §error-handling block asserts `Error: can't stop backup_service` for dead/missing → treat latter as authoritative.
      6c. Call `os.kill(pid, signal.SIGTERM)`.
      6d. Remove `./logs/backup_service.pid`.
      6e. Log `[dd/mm/yyyy hh:mm] backup_service stopped`.
  7. **Unknown commands**
     7a. Default branch in argument parser logs `Error: unknown instruction` to `./logs/backup_manager.log` (CLI owns this; audit.md:145 example `cat logs/backup_service.log` is a typo — invalid CLI commands cannot reach daemon logs).
  8. **Logging** — every function logs to `./logs/backup_manager.log` with format `[dd/mm/yyyy hh:mm] Message`.
  9. **Error handling** — wrap I/O, process ops in `try`/`except`.
  10. **Unit tests** — one test per item above covering success + error paths (see §5 Unit Test Coverage). All tests pass before phase 3.

### **Developer 3**
* **Role**: Daemon Service & Storage Architect.
* **Spec references**: [`docs/requirements.md`](docs/requirements.md) §Second script, §Logging, §Testing.
* **Deliverable**: `backup_service.py` + `tests/unit/test_backup_service.py`.
* **Implementation steps**:
  1. **Process startup**
     1a. On launch: write own PID to `./logs/backup_service.pid` via `os.getpid()`.
     1b. Log `[dd/mm/yyyy hh:mm] Service started`.
  2. **Main loop structure**
     2a. Infinite `while True` loop.
     2b. Sleep `time.sleep(45)` at end of each iteration.
     2c. Wrap loop body in `try`/`except` — never crash.
  3. **Schedule file reading**
     3a. Open `backup_schedules.txt`.
     3b. If file missing: log `Error: cannot open backup_schedules`, skip iteration.
     3c. Parse each line: split on `;` into `path`, `time`, `name`.
     3d. Skip malformed lines (log warning optional).
  4. **Time matching**
     4a. Compare current local time (`datetime.now().hour`, `.minute`) with schedule time.
     4b. If time matches → proceed to backup.
      4c. If schedule time is earlier than current time → remove schedule line from file (time already passed).
  5. **Deduplication**
     5a. Track executed backups in memory: set of `(date_str, schedule_line)`.
     5b. Skip if already run today for that schedule.
     5c. Allow retrigger on different calendar day.
  6. **Tar archive creation**
     6a. Check target path exists. If missing: log error, skip.
     6b. Create `./backups/{backup_name}.tar` using `tarfile.TarFile`.
     6c. Add entire directory tree with `arcname` preserving hierarchy.
     6d. Log `Backup done for <path> in backups/<name>.tar`.
     6e. On failure: log error, do not crash loop.
  7. **Logging** — all events to `./logs/backup_service.log` with format `[dd/mm/yyyy hh:mm] Message`.
  8. **Error handling** — wrap I/O, tar ops, file ops in `try`/`except`.
  9. **Unit tests** — one test per item above covering success + error paths (see §5 Unit Test Coverage). All tests pass before phase 3.

---

## 4. Phase Schedule & Timeline

```
                     ┌───────────────────────────────────┐
                     │ Phase 1: Planning & Setup         │
                     │ (Contracts & Best Practices)      │
                     └─────────────────┬─────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
      ┌───────────────────────────┐         ┌───────────────────────────┐
      │ Phase 2A: CLI Development │         │ Phase 2B: Daemon Dev      │
      │ (Developer 2)             │         │ (Developer 3)             │
      └─────────────┬─────────────┘         └─────────────┬─────────────┘
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       ▼
                     ┌───────────────────────────────────┐
                     │ Phase 3: Integration & QA         │
                     │ (Developer 1 - Audit Script)      │
                     └─────────────────┬─────────────────┘
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │ Phase 4: Release & Handover       │
                     └───────────────────────────────────┘
```

### Phase Details

**Phase 1: Planning & Setup** (Dev 1)
- [ ] Set up project skeleton: `AGENTS.md`, `README.md`, `development_plan.md`, `docs/requirements.md`, `docs/audit.md`, `development_plan.md`.
- [ ] Verify directory structure per `AGENTS.md`.
- [ ] Confirm all 3 developers have access and understand contracts.

**Phase 2: Parallel Implementation**

*Phase 2A — Dev 2 (CLI)*
- [ ] **Step 1**: Implement `validate_schedule()` — parse and validate `"path;hh:mm;name"` (per requirements.md §create).
- [ ] **Step 2**: Implement `add_schedule()` — write valid schedule to `backup_schedules.txt`, log result.
- [ ] **Step 3**: Implement `list_schedules()` — read file, print 0-indexed lines.
- [ ] **Step 4**: Implement `delete_schedule(index)` — remove line, re-index remainder.
- [ ] **Step 5**: Implement `list_backups()` — scan `./backups/` for `.tar` files.
- [ ] **Step 6**: Implement `start_service()` — PID check → `subprocess.Popen` → write PID → log.
- [ ] **Step 7**: Implement `stop_service()` — read PID → `os.kill` → clean PID file → log.
- [ ] **Step 8**: Implement `handle_command()` — arg parser dispatching to steps 2–7, default logs `Error: unknown instruction`.
- [ ] **Step 9**: Implement `log()` — append to `./logs/backup_manager.log` with `[dd/mm/yyyy hh:mm]` timestamp.
- [ ] **Step 10**: Wrap all I/O/process ops in `try`/`except`.
- [ ] **Step 11**: Write `tests/unit/test_backup_manager.py` — one test per requirement above, success + error.
- [ ] **Gate**: `python3 -m unittest discover -s tests/unit -v` passes 100%.

*Phase 2B — Dev 3 (Daemon)*
- [ ] **Step 1**: Implement `register_pid()`/`unregister_pid()` — write/clean `./logs/backup_service.pid`.
- [ ] **Step 2**: Implement main daemon loop — `while True` with `time.sleep(45)`.
- [ ] **Step 3**: Implement `parse_schedule()` — line → `(path, time, name)` tuple.
- [ ] **Step 4**: Implement `time_matches(hh:mm)` — compare to `datetime.now()` hour/minute.
- [ ] **Step 5**: Implement deduplication — track executed `(date, schedule)` pairs, skip repeats.
- [ ] **Step 6**: Implement `create_backup(path, name)` — `tarfile` compression to `./backups/`.
- [ ] **Step 7**: Handle missing target folder gracefully (log, skip, no crash).
- [ ] **Step 8**: Handle missing `backup_schedules.txt` — log `Error: cannot open backup_schedules`, continue loop.
- [ ] **Step 9**: Implement `log()` — append to `./logs/backup_service.log` with `[dd/mm/yyyy hh:mm]` timestamp.
- [ ] **Step 10**: Wrap all I/O/tar ops in `try`/`except`.
- [ ] **Step 11**: Write `tests/unit/test_backup_service.py` — one test per requirement above, success + error.
- [ ] **Gate**: `python3 -m unittest discover -s tests/unit -v` passes 100%.

**Phase 3: Integration & QA** (Dev 1)
> **Source-of-truth note**: `docs/` (requirements.md, audit.md, readme.md) are canonical. This plan must not contradict them. Where `audit.md` example outputs (`Schedule created` L109, `Error: service already running` L76) differ from canonical spec strings in `requirements.md`/`readme.md` (`New schedule added: <string>`, `Error: backup_service already running`), the canonical spec wins; audit examples are illustrative only. Implementations and tests must assert canonical strings.

- [ ] Merge Dev 2 and Dev 3 branches.
- [ ] **Gate**: Run `python3 -m unittest discover -s tests/unit -v` — must pass before proceeding.
- [ ] **Integration tests** (`tests/integration/test_cli_daemon.py`):
  - [ ] Write test: `start` spawns real process visible via `ps`.
  - [ ] Write test: `stop` terminates process, cleans PID file.
  - [ ] Write test: double `start` blocked with `Error: backup_service already running`.
  - [ ] Write test: full flow — `create` → `start` → backup trigger → `backups` → `stop`.
- [ ] **E2E audit tests** (`tests/e2e/test_audit_compliance.py`) — every `docs/audit.md` question maps to a test method:

  | Audit Question | Test Method | What It Validates |
  |---|---|---|
  | Fresh env `rm -dr logs backups backup_schedules.txt` | `test_clean_state` | All artifacts removed, no crash on missing dirs |
  | `backup_manager.py` and `backup_service.py` present | `test_scripts_present` | Both files exist in project root |
  | `create "test2;18:15;backup_test2"` | `test_create_schedule_creates_file` | `backup_schedules.txt` created with correct content |
  | `cat backup_schedules.txt` format matches | `test_schedule_content_format` | Line matches `path;hh:mm;name` pattern |
  | `stop` on stopped daemon | `test_stop_no_daemon` | Logs `Error: can't stop backup_service` |
  | `logs/` folder and `backup_manager.log` created | `test_logs_folder_created` | Directory and log file exist |
  | Log content format `[dd/mm/yyyy hh:mm] Error: ...` | `test_log_format_and_content` | Timestamp + message pattern |
  | `list` with 0-indexed output | `test_list_indexed_output` | Lines prefixed `0:`, `1:`, `2:` |
  | `delete 1` removes correct line | `test_delete_removes_index` | Line removed, file rewritten |
  | Re-indexing after delete | `test_delete_reindexes` | Index 2 becomes 1 after delete |
  | `start` spawns daemon process | `test_start_spawns_process` | `ps` shows `backup_service.py`, PID file exists |
  | Double `start` prevention | `test_double_start_blocked` | Second `start` logs already-running error |
  | Manual backup at matching time | `test_backup_at_scheduled_time` | `.tar` created, non-empty, correct files |
  | Passed time does not trigger | `test_passed_time_no_backup` | No `.tar` for past schedule |
  | Tar contents match original | `test_tar_contents_match_original` | `tarfile` verify names, sizes, hierarchy |
  | Error: unknown instruction | `test_unknown_instruction_logged` | Logs `Error: unknown instruction` |
  | Error: malformed schedule | `test_malformed_schedule_logged` | Logs `Error: malformed schedule: <string>` |
  | Error: can't find backups directory | `test_missing_backups_dir` | Logs `Error: can't find backups directory` |
  | Error: backup_service already running | `test_already_running_logged` | Logs error on duplicate start |
  | Error: cannot open backup_schedules | `test_no_schedule_file_daemon` | Daemon logs error when file missing |
  | `.zip` folder backup | `test_zip_folder_backup` | `.zip` folder backed up as `.tar`, files match |
  | try/except in source | `test_try_except_in_source` | Both `.py` files contain try and except |
- [ ] Run full test suite: `python3 -m unittest discover -s tests -v`.
- [ ] Manual exploratory walkthrough of `docs/audit.md`.
- [ ] Code review: verify `try`/`except` in both scripts, edge cases handled.

**Phase 4: Release & Handover** (Dev 1)
- [ ] Finalize `README.md` — update any config changes.
- [ ] Verify all docs cross-references are accurate.
- [ ] Tag release.

---

## 5. Testing Strategy

### Framework
All tests use Python's built-in `unittest` — no external dependencies.

### Test File Mapping

| File | Owner | Phase | Purpose |
|---|---|---|---|
| `tests/unit/test_backup_manager.py` | Dev 2 | Phase 2 | Unit tests for every CLI function |
| `tests/unit/test_backup_service.py` | Dev 3 | Phase 2 | Unit tests for every daemon function |
| `tests/integration/test_cli_daemon.py` | Dev 1 | Phase 3 | Process lifecycle, start/stop/restart |
| `tests/e2e/test_audit_compliance.py` | Dev 1 | Phase 3 | Every audit.md question → test method |

### Dev 2 Unit Test Coverage (`test_backup_manager.py`)
- Schedule parsing: valid format, malformed (missing parts, invalid time, empty)
- `create`: correct line written to `backup_schedules.txt`
- `create`: logs `Error: malformed schedule: <string>` for bad input
- `list`: 0-indexed output, correct content
- `list`: logs `Error: can't find backup_schedules.txt` when missing
- `delete [index]`: removes line, re-indexes correctly
- `delete`: logs `Error: can't find schedule at index <index>` for bad index
- `delete`: logs `Error: can't find backup_schedules.txt` when missing
- `backups`: lists `.tar` files from `./backups`
- `backups`: logs `Error: can't find backups directory` when missing
- `start`: calls `subprocess.Popen` with `start_new_session=True`
- `start`: writes PID to `logs/backup_service.pid`
- `start`: logs `Error: backup_service already running` on double launch
- `stop`: calls `os.kill(pid, signal.SIGTERM)`, cleans PID file
- `stop`: logs `Error: can't stop backup_service` when no daemon
- Unknown commands: logs `Error: unknown instruction`
- Log format: `[dd/mm/yyyy hh:mm] Message`
- Error handling: source uses `try`/`except`

### Dev 3 Unit Test Coverage (`test_backup_service.py`)
- Schedule line parsing: valid 3-part, malformed, empty
- Time matching: match returns true, mismatch returns false
- Passed-time schedules: do not trigger
- Deduplication: same schedule not triggered twice within same day
- Deduplication: same time on different day does retrigger
- PID registration: writes correct PID to `logs/backup_service.pid`
- PID cleanup: removes file on stop
- Tar creation: files present, directory hierarchy preserved
- Tar integrity: files non-empty, not corrupted
- Missing folder: logs error, skips gracefully (no crash)
- Backup success log: `Backup done for <path> in backups/<name>.tar`
- Missing schedule file: logs `Error: cannot open backup_schedules`
- Log format: `[dd/mm/yyyy hh:mm] Message`
- Error handling: source uses `try`/`except`
- Sleep constant: 45 seconds

### Running Tests

```bash
python3 -m unittest discover -s tests -v          # all
python3 -m unittest discover -s tests/unit -v      # phase 2 gate
python3 -m unittest discover -s tests/integration -v
python3 -m unittest discover -s tests/e2e -v
```

---

## 6. Verification Checklist (Dev 1 / QA)

The following checklist must be satisfied before marking the project complete:

1. [ ] **Fresh Environment Clean**: Running `rm -dr logs backups backup_schedules.txt` leaves system in a clean state.
2. [ ] **CLI Execution**:
   - `python3 ./backup_manager.py create "test2;18:15;backup_test2"` creates `backup_schedules.txt` containing `test2;18:15;backup_test2`.
   - Adding a malformed schedule logs error to `./logs/backup_manager.log` and rejects write.
3. [ ] **Process Launch & Kill**:
   - `python3 ./backup_manager.py start` spawns `backup_service.py` which runs in background.
   - A subsequent `start` command logs `Error: backup_service already running` and does not spawn a new one.
   - `python3 ./backup_manager.py stop` successfully terminates daemon and cleans up the PID file.
   - Running `stop` when daemon isn't active logs `Error: can't stop backup_service`.
4. [ ] **Execution Integrity**:
   - Scheduled tasks execute at the exact hour and minute matching local system time.
   - Target backups are archived as `.tar` files in `./backups`.
   - Extracts from generated tarballs (`tar -tvf backup_test.tar`) match original target folders without corruption.
   - Passed times do not trigger immediate backups.
   - No duplicate backups trigger within the 60-second window.
5. [ ] **Robust Error Logging**:
   - Missing configuration files yield appropriate error logs instead of code crashes.
   - Log folders and target folders are verified before access.
