import threading
import time
from datetime import datetime
from cli.config import SERVICE_SLEEP_SECONDS, SERVICE_LOG_FILE, SCHEDULES_FILE
from cli.logger import log
from daemon.pid import register_pid, install_signal_handlers
from daemon.schedule_reader import read_schedules, parse_schedule
from daemon.backup import create_backup

def time_matches(hh, mm, now):
    return now.hour == hh and now.minute == mm

def _run_backup_async(path, name, key, executed, in_progress):
    try:
        if create_backup(path, name):
            executed.add(key)
    finally:
        in_progress.discard(key)

def run_cycle(executed, in_progress, state, now=None):
    """Check schedules once, dispatching any backup whose time matches now.

    Each matching backup runs on its own thread so a slow tar doesn't delay
    the next schedule check. Returns the list of threads started, so tests
    can join them for deterministic assertions.

    `executed` is a set of (date_str, schedule_line) pairs already backed
    up today, used to avoid double-triggering within the same minute.
    `in_progress` is a set of the same kind of key for backups that have
    been dispatched but haven't finished yet, so a slow backup isn't
    dispatched a second time on the next cycle.
    `state` is a dict of cross-cycle flags (e.g. whether the schedule file
    was already reported missing, so we don't log the same error every cycle).
    """
    now = now or datetime.now()
    date_str = now.strftime("%d/%m/%Y")

    # Drop dedup entries from previous days so `executed` doesn't grow
    # forever across a long-running process.
    stale = {key for key in executed if key[0] != date_str}
    executed.difference_update(stale)

    lines = read_schedules(log_missing=not state.get("schedule_missing", False))
    if lines is None:
        state["schedule_missing"] = True
        return []
    state["schedule_missing"] = False

    updated_lines = []
    file_changed = False

    threads = []
    for line in lines:
        parsed = parse_schedule(line)
        if parsed is None:
            updated_lines.append(line)
            continue

        path, hh, mm, name = parsed

        if hh * 60 + mm < now.hour * 60 + now.minute:
            file_changed = True
            continue

        updated_lines.append(line)

        if not time_matches(hh, mm, now):
            continue

        key = (date_str, line)
        if key in executed or key in in_progress:
            full_name = f"{name}_{now.strftime('%d-%m-%Y_%H:%M')}"
            log(f"Error: backup '{full_name}.tar' already exists, skipping", SERVICE_LOG_FILE)
            continue

        in_progress.add(key)
        thread = threading.Thread(
            target=_run_backup_async,
            args=(path, name, key, executed, in_progress),
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    if file_changed:
        try:
            with open(SCHEDULES_FILE, "w") as f:
                f.write("\n".join(updated_lines) + ("\n" if updated_lines else ""))
        except Exception as e:
            log(f"Error: cannot update backup_schedules: {e}", SERVICE_LOG_FILE)

    return threads

def main():
    register_pid()
    install_signal_handlers()
    log("Service started", SERVICE_LOG_FILE)

    executed = set()
    in_progress = set()
    state = {}

    while True:
        try:
            run_cycle(executed, in_progress, state)
        except Exception as e:
            log(f"Error: unexpected failure in service loop: {e}", SERVICE_LOG_FILE)
        time.sleep(SERVICE_SLEEP_SECONDS)

if __name__ == "__main__":
    main()
