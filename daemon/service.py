import time
from datetime import datetime
from cli.config import SERVICE_SLEEP_SECONDS, SERVICE_LOG_FILE
from cli.logger import log
from daemon.pid import register_pid, install_sigterm_handler
from daemon.schedule_reader import read_schedules, parse_schedule
from daemon.backup import create_backup

def time_matches(hh, mm, now):
    return now.hour == hh and now.minute == mm

def run_cycle(executed, now=None):
    """Check schedules once, running any backup whose time matches now.

    `executed` is a set of (date_str, schedule_line) pairs already backed
    up today, used to avoid double-triggering within the same minute.
    """
    now = now or datetime.now()
    date_str = now.strftime("%d/%m/%Y")

    lines = read_schedules()
    if lines is None:
        return

    for line in lines:
        parsed = parse_schedule(line)
        if parsed is None:
            continue

        path, hh, mm, name = parsed

        if not time_matches(hh, mm, now):
            continue

        if (date_str, line) in executed:
            continue

        if create_backup(path, name):
            executed.add((date_str, line))

def main():
    register_pid()
    install_sigterm_handler()
    log("Service started", SERVICE_LOG_FILE)

    executed = set()

    while True:
        try:
            run_cycle(executed)
        except Exception as e:
            log(f"Error: unexpected failure in service loop: {e}", SERVICE_LOG_FILE)
        time.sleep(SERVICE_SLEEP_SECONDS)

if __name__ == "__main__":
    main()
