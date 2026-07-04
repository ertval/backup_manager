# Dev 3 Daemon Implementation Audit Report

This report provides a detailed audit of the background scheduling daemon (`backup_service.py` and the `daemon/` module) implemented by **Developer 3**. It evaluates compliance with the project specifications, reviews security issues, identifies functional/logic bugs, and assesses code quality.

---

## Executive Summary

The daemon implementation is **highly compliant** and **fully functional**. Developer 3 has successfully met almost all specs, deliverables, and unit test requirements. All 19 unit tests in `tests/unit/test_backup_service.py` pass and cover both success and error paths. 

However, several security concerns, edge cases, and design issues have been identified during this audit. Specifically, a path traversal vulnerability in the backup name exists, a potential log-spam bug when the schedule file is missing, an unbounded memory growth in the executed schedule tracker, and incomplete signal handling.

### Key Findings
1. **Requirements Compliance**: Meets all functional specs for scheduling, parsing, execution, and deduplication.
2. **Security Vulnerability**: A risk of path traversal exists in the backup name, which allows writing tar archives outside the designated backups directory.
3. **Log-Spam Bug**: If the schedule file is missing, the daemon logs an error every 45 seconds, rapidly bloating the logs.
4. **Memory Leak**: The in-memory execution history (`executed`) grows indefinitely, lacking any pruning logic.
5. **Incomplete Signal Handling**: Only `SIGTERM` is handled; terminating the daemon via `SIGINT` (Ctrl+C) or other signals leaves stale PID files behind.
6. **Blocking Operations**: Tarball compression runs synchronously on the main thread, potentially blocking the scheduling loop and causing missed backups.

---

## 1. Requirements Compliance Matrix

| Command / Feature | Expected Behavior & Log Contract | Actual Behavior / Log | Status | Compliance Issue / Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Process Startup** | On launch, write own PID to `./logs/backup_service.pid`. Log `Service started`. | Own PID written to `PID_FILE`. Logs `Service started` to `backup_service.log`. | **PASSED** | Correctly implemented in `pid.py` and `service.py`. |
| **Main Loop** | Run in an infinite loop. Sleep `45` seconds at end of each iteration. Wrap loop body in `try`/`except`. | Runs `while True` loop with 45-second sleep. Loop body wrapped in `try`/`except`. | **PASSED** | Robust loop execution, prevents crashing on individual failures. |
| **Schedule Reading**| Open `backup_schedules.txt`. If file missing, log `Error: cannot open backup_schedules` and skip. | Reads schedules correctly. Logs exact error message on missing file. | **PASSED** | Correctly implemented, though missing file results in log spam. |
| **Time Matching** | Check current local time (hour and minute). If matches, trigger backup. If time passed, skip. | Compares schedule hour/minute to `datetime.now()`. Past/future times are skipped. | **PASSED** | Logic is correct and matches requirements. |
| **Deduplication** | Skip if already run today for that schedule. Allow retrigger on different calendar day. | Uses in-memory set of `(date_str, schedule_line)` to deduplicate. | **PASSED** | Deduplication behaves as expected, although set size is unbounded. |
| **Tar Creation** | Verify path exists. Create `./backups/{name}.tar` preserving hierarchy. Log success/error. | Uses `tarfile` module. Compresses correctly. Logs success/error exact strings. | **PASSED** | Preserves directory structure; handles missing source directories gracefully. |
| **Logging Format**| Log format: `[dd/mm/yyyy hh:mm] Message` | Matches format: `[dd/mm/yyyy hh:mm] Message` | **PASSED** | Correct date/time format mapping via `cli/logger.py`. |
| **Error Handling**| Wrap I/O, tar, and file operations in `try`/`except`. | Uses `try`/`except` around all critical system operations. | **PASSED** | Defensive error handling prevents daemon termination. |
| **Unit Tests** | `tests/unit/test_backup_service.py` covers success/error paths. | 19 tests in `tests/unit/test_backup_service.py` passing. | **PASSED** | Excellent test coverage. |

---

## 2. Detailed Technical Audit & Bugs

### A. Missing Schedule File Log-Spam Bug
In [daemon/schedule_reader.py](file:///home/ertval/code/zone-modules/backup_manager/daemon/schedule_reader.py#L4-L12), if `backup_schedules.txt` does not exist, `read_schedules()` catches the error, logs the failure, and returns `None`:
```python
def read_schedules():
    try:
        with open(SCHEDULES_FILE, "r") as f:
            return [l.rstrip("\n") for l in f.readlines() if l.strip()]
    except Exception:
        log("Error: cannot open backup_schedules", SERVICE_LOG_FILE)
        return None
```
Because the daemon calls `read_schedules()` on every single loop iteration (every 45 seconds), if the file is deleted or has not been created, the log file `./logs/backup_service.log` will be spammed with the error message every 45 seconds. This causes unnecessary disk write activity and bloats the log files.

**Remediation**: The daemon should only log the error once when it transitions from "file exists" to "file missing" (or suppress repeated identical logs until the state changes).

### B. Unbounded Memory Leak in Deduplication Set
In [daemon/service.py](file:///home/ertval/code/zone-modules/backup_manager/daemon/service.py#L41-L53), the daemon instantiates an empty set `executed` and passes it to `run_cycle`:
```python
def main():
    ...
    executed = set()
    while True:
        try:
            run_cycle(executed)
        ...
```
Inside `run_cycle`, `(date_str, line)` pairs are added to `executed` whenever a backup completes. However, there is no logic to clean up or prune old dates from the `executed` set. If the daemon runs continuously for months, this set will grow indefinitely, leading to a slow memory leak.

**Remediation**: At the start of `run_cycle`, prune entries from `executed` where the date component is not equal to `date_str` (the current date).

### C. Incomplete Signal Handling (Ctrl+C / SIGINT)
In [daemon/pid.py](file:///home/ertval/code/zone-modules/backup_manager/daemon/pid.py#L24-L29), a signal handler is installed only for `SIGTERM`:
```python
def handle_sigterm(signum, frame):
    unregister_pid()
    raise SystemExit(0)

def install_sigterm_handler():
    signal.signal(signal.SIGTERM, handle_sigterm)
```
If the daemon is executed in the foreground (e.g., during debugging or manual execution) and terminated using `SIGINT` (Ctrl+C), or if it receives `SIGHUP` or `SIGQUIT`, the PID file `./logs/backup_service.pid` is not removed. This leaves a stale PID file behind, which may block future invocations of `backup_manager.py start` from launching the service.

**Remediation**: Register `handle_sigterm` (or a generic cleanup handler) for `signal.SIGINT` as well.

---

## 3. Security Analysis

### Path Traversal / Arbitrary File Creation Vulnerability
In [daemon/backup.py](file:///home/ertval/code/zone-modules/backup_manager/daemon/backup.py#L12-L18), the target tar archive path is created by directly joining `BACKUPS_DIR` with the user-provided schedule name:
```python
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        tar_path = os.path.join(BACKUPS_DIR, f"{name}.tar")
```
If `backup_schedules.txt` is modified by an attacker, or if the CLI validates input weakly, a schedule name containing directory traversal characters (e.g., `../../etc/cron.d/malicious`) will bypass `BACKUPS_DIR` limits.
When `tarfile.open(tar_path, "w")` is executed, the daemon will write the tar file to the resolved location (e.g., `/etc/cron.d/malicious.tar`), resulting in an **Arbitrary File Write / Path Traversal** vulnerability. If the daemon runs with high privileges, this can lead to system compromise.

**Remediation**: Sanitize `name` to ensure it does not contain path traversal characters:
```python
# Check that name does not escape the backups directory
abs_backups_dir = os.path.abspath(BACKUPS_DIR)
abs_tar_path = os.path.abspath(os.path.join(BACKUPS_DIR, f"{name}.tar"))
if not abs_tar_path.startswith(abs_backups_dir + os.sep):
    # Reject/raise exception
```

---

## 4. Code Quality & Design Observations

1. **Synchronous I/O Block (Potential DoS)**:
   The daemon archives and compresses directories using Python's synchronous `tarfile` library inside the main thread. If a backup target is very large (e.g., several gigabytes), the main thread will block for minutes or hours. During this period, the daemon cannot process other scheduled backups, causing them to be missed.
2. **Global configuration dependency**:
   The module imports settings from the `cli` package (e.g., `cli.config`). While this sharing is convenient, it couples the daemon tightly to the CLI codebase, making it harder to package or run the daemon independently.
3. **Robust Unit Tests**:
   Developer 3 has written a comprehensive unit test suite in [tests/unit/test_backup_service.py](file:///home/ertval/code/zone-modules/backup_manager/tests/unit/test_backup_service.py). The tests use `tempfile.TemporaryDirectory` to isolate file operations, ensuring tests do not contaminate the local repository files.

---

## 5. Actionable Recommendations & Remediation Plan

To harden the daemon implementation prior to production release, the following remediations should be implemented:

1. **Sanitize Backup Names**: Protect against path traversal by resolving and validating paths in `daemon/backup.py` before writing files.
2. **Mitigate Log Spam**: Add a state check in `daemon/schedule_reader.py` so that a missing schedule file is logged only once, rather than every 45 seconds.
3. **Prune Execution Cache**: Periodically clear entries from the `executed` set that belong to previous days to prevent unbounded memory growth.
4. **Register Additional Signal Handlers**: Capture `SIGINT` (and optionally `SIGHUP`) to ensure `backup_service.pid` is cleaned up under all normal termination scenarios.
