import os
import re
import signal
import tarfile
import tempfile
import threading
import unittest
from datetime import datetime
from unittest.mock import patch

from cli.config import SERVICE_LOG_FILE, PID_FILE, BACKUPS_DIR, SERVICE_SLEEP_SECONDS
from daemon import backup, pid, schedule_reader, service


class DaemonTestCase(unittest.TestCase):
    """Runs each test inside its own temp directory so relative paths
    (./logs, ./backups, ./backup_schedules.txt) never touch the real project."""

    def setUp(self):
        self._old_cwd = os.getcwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)
        os.makedirs("logs", exist_ok=True)
        os.makedirs("backups", exist_ok=True)

    def tearDown(self):
        os.chdir(self._old_cwd)
        self._tmpdir.cleanup()

    def run_cycle_sync(self, executed, in_progress, state, now=None):
        """Run one cycle and block until any dispatched backups finish,
        so callers can assert on their effects deterministically."""
        threads = service.run_cycle(executed, in_progress, state, now=now)
        for t in threads:
            t.join(timeout=5)
        return threads


class TestScheduleParsing(DaemonTestCase):
    def test_parse_valid_schedule(self):
        self.assertEqual(
            schedule_reader.parse_schedule("testing;18:21;backup_test"),
            ("testing", 18, 21, "backup_test"),
        )

    def test_parse_malformed_missing_parts(self):
        self.assertIsNone(schedule_reader.parse_schedule("testing;18:21"))

    def test_parse_malformed_bad_time(self):
        self.assertIsNone(schedule_reader.parse_schedule("testing;25:99;backup_test"))

    def test_parse_empty_line(self):
        self.assertIsNone(schedule_reader.parse_schedule(""))

    def test_parse_rejects_path_traversal_name(self):
        self.assertIsNone(schedule_reader.parse_schedule("testing;18:21;../../etc/evil"))

    def test_parse_rejects_name_with_directory_separator(self):
        self.assertIsNone(schedule_reader.parse_schedule("testing;18:21;sub/evil"))

    def test_read_schedules_missing_file_logs_error(self):
        result = schedule_reader.read_schedules()
        self.assertIsNone(result)
        with open(SERVICE_LOG_FILE) as f:
            self.assertIn("Error: cannot open backup_schedules", f.read())

    def test_read_schedules_skips_blank_lines(self):
        with open("backup_schedules.txt", "w") as f:
            f.write("testing;18:21;backup_test\n\n")
        self.assertEqual(schedule_reader.read_schedules(), ["testing;18:21;backup_test"])


class TestTimeMatching(DaemonTestCase):
    def test_time_matches_true(self):
        now = datetime(2026, 7, 4, 18, 21)
        self.assertTrue(service.time_matches(18, 21, now))

    def test_time_matches_false(self):
        now = datetime(2026, 7, 4, 18, 21)
        self.assertFalse(service.time_matches(13, 11, now))

    def test_passed_time_schedule_does_not_trigger(self):
        os.makedirs("testing", exist_ok=True)
        with open("backup_schedules.txt", "w") as f:
            f.write("testing;13:11;passed_time_backup\n")

        now = datetime(2026, 7, 4, 18, 21)
        self.run_cycle_sync(set(), set(), {}, now=now)

        self.assertFalse(os.path.exists(os.path.join(BACKUPS_DIR, "passed_time_backup.tar")))


class TestDeduplication(DaemonTestCase):
    def test_same_schedule_not_triggered_twice_same_day(self):
        os.makedirs("testing", exist_ok=True)
        with open("backup_schedules.txt", "w") as f:
            f.write("testing;18:21;backup_test\n")

        now = datetime(2026, 7, 4, 18, 21)
        executed = set()
        in_progress = set()
        self.run_cycle_sync(executed, in_progress, {}, now=now)
        self.run_cycle_sync(executed, in_progress, {}, now=now)

        with open(SERVICE_LOG_FILE) as f:
            occurrences = f.read().count("Backup done for testing in backups/backup_test.tar")
        self.assertEqual(occurrences, 1)

    def test_same_schedule_retriggers_on_different_day(self):
        os.makedirs("testing", exist_ok=True)
        with open("backup_schedules.txt", "w") as f:
            f.write("testing;18:21;backup_test\n")

        day1 = datetime(2026, 7, 4, 18, 21)
        day2 = datetime(2026, 7, 5, 18, 21)
        executed = set()
        in_progress = set()
        self.run_cycle_sync(executed, in_progress, {}, now=day1)
        self.run_cycle_sync(executed, in_progress, {}, now=day2)

        with open(SERVICE_LOG_FILE) as f:
            occurrences = f.read().count("Backup done for testing in backups/backup_test.tar")
        self.assertEqual(occurrences, 2)

    def test_executed_set_prunes_entries_from_previous_days(self):
        os.makedirs("testing", exist_ok=True)
        with open("backup_schedules.txt", "w") as f:
            f.write("testing;18:21;backup_test\n")

        day1 = datetime(2026, 7, 4, 18, 21)
        day2 = datetime(2026, 7, 5, 18, 21)
        executed = set()
        in_progress = set()
        self.run_cycle_sync(executed, in_progress, {}, now=day1)
        self.assertEqual(executed, {(day1.strftime("%d/%m/%Y"), "testing;18:21;backup_test")})

        self.run_cycle_sync(executed, in_progress, {}, now=day2)
        self.assertEqual(executed, {(day2.strftime("%d/%m/%Y"), "testing;18:21;backup_test")})

    def test_in_progress_backup_not_dispatched_twice_concurrently(self):
        os.makedirs("testing", exist_ok=True)
        with open("backup_schedules.txt", "w") as f:
            f.write("testing;18:21;backup_test\n")

        now = datetime(2026, 7, 4, 18, 21)
        release = threading.Event()
        call_count = {"n": 0}

        def slow_backup(path, name):
            call_count["n"] += 1
            release.wait(timeout=5)
            return True

        executed = set()
        in_progress = set()
        with patch.object(service, "create_backup", side_effect=slow_backup):
            threads1 = service.run_cycle(executed, in_progress, {}, now=now)
            # Same tick, backup from threads1 is still running (blocked on `release`).
            threads2 = service.run_cycle(executed, in_progress, {}, now=now)
            release.set()
            for t in threads1 + threads2:
                t.join(timeout=5)

        self.assertEqual(call_count["n"], 1)
        self.assertEqual(len(threads2), 0)


class TestNonBlockingScheduler(DaemonTestCase):
    def test_run_cycle_returns_before_slow_backup_finishes(self):
        os.makedirs("testing", exist_ok=True)
        with open("backup_schedules.txt", "w") as f:
            f.write("testing;18:21;backup_test\n")

        now = datetime(2026, 7, 4, 18, 21)
        started = threading.Event()
        release = threading.Event()

        def slow_backup(path, name):
            started.set()
            release.wait(timeout=5)
            return True

        with patch.object(service, "create_backup", side_effect=slow_backup):
            threads = service.run_cycle(set(), set(), {}, now=now)
            # run_cycle already returned even though the backup is still
            # blocked on `release` -- proves the scheduler isn't waiting on it.
            self.assertTrue(started.wait(timeout=1))
            self.assertTrue(any(t.is_alive() for t in threads))
            release.set()
            for t in threads:
                t.join(timeout=5)


class TestMissingScheduleFileLogging(DaemonTestCase):
    def test_missing_schedule_file_logs_only_once_across_cycles(self):
        state = {}
        self.run_cycle_sync(set(), set(), state, now=datetime(2026, 7, 4, 18, 21))
        self.run_cycle_sync(set(), set(), state, now=datetime(2026, 7, 4, 18, 22))
        self.run_cycle_sync(set(), set(), state, now=datetime(2026, 7, 4, 18, 23))

        with open(SERVICE_LOG_FILE) as f:
            occurrences = f.read().count("Error: cannot open backup_schedules")
        self.assertEqual(occurrences, 1)

    def test_missing_schedule_file_logs_again_after_reappearing(self):
        state = {}
        self.run_cycle_sync(set(), set(), state, now=datetime(2026, 7, 4, 18, 21))

        with open("backup_schedules.txt", "w") as f:
            f.write("")
        self.run_cycle_sync(set(), set(), state, now=datetime(2026, 7, 4, 18, 22))

        os.remove("backup_schedules.txt")
        self.run_cycle_sync(set(), set(), state, now=datetime(2026, 7, 4, 18, 23))

        with open(SERVICE_LOG_FILE) as f:
            occurrences = f.read().count("Error: cannot open backup_schedules")
        self.assertEqual(occurrences, 2)


class TestPidFile(DaemonTestCase):
    def test_register_pid_writes_own_pid(self):
        pid.register_pid()
        with open(PID_FILE) as f:
            self.assertEqual(f.read().strip(), str(os.getpid()))

    def test_unregister_pid_removes_file(self):
        pid.register_pid()
        pid.unregister_pid()
        self.assertFalse(os.path.exists(PID_FILE))

    def test_handle_shutdown_signal_cleans_up_pid_and_exits(self):
        pid.register_pid()
        with self.assertRaises(SystemExit):
            pid.handle_shutdown_signal(signal.SIGTERM, None)
        self.assertFalse(os.path.exists(PID_FILE))

    def test_install_signal_handlers_registers_sigterm_and_sigint(self):
        original_term = signal.getsignal(signal.SIGTERM)
        original_int = signal.getsignal(signal.SIGINT)
        try:
            pid.install_signal_handlers()
            self.assertIs(signal.getsignal(signal.SIGTERM), pid.handle_shutdown_signal)
            self.assertIs(signal.getsignal(signal.SIGINT), pid.handle_shutdown_signal)
        finally:
            signal.signal(signal.SIGTERM, original_term)
            signal.signal(signal.SIGINT, original_int)


class TestBackupCreation(DaemonTestCase):
    def test_tar_created_with_hierarchy_and_non_empty_files(self):
        os.makedirs("testing/subdir", exist_ok=True)
        with open("testing/file1", "w") as f:
            f.write("hello")
        with open("testing/subdir/file2", "w") as f:
            f.write("world")

        result = backup.create_backup("testing", "backup_test")
        self.assertTrue(result)

        tar_path = os.path.join(BACKUPS_DIR, "backup_test.tar")
        self.assertTrue(os.path.exists(tar_path))

        with tarfile.open(tar_path) as tar:
            names = tar.getnames()
            self.assertIn("testing/file1", names)
            self.assertIn("testing/subdir/file2", names)
            self.assertGreater(tar.getmember("testing/file1").size, 0)

    def test_backup_success_log_format(self):
        os.makedirs("testing", exist_ok=True)
        backup.create_backup("testing", "backup_test")
        with open(SERVICE_LOG_FILE) as f:
            self.assertIn("Backup done for testing in backups/backup_test.tar", f.read())

    def test_missing_source_folder_logs_error_and_skips(self):
        result = backup.create_backup("does_not_exist", "backup_test")
        self.assertFalse(result)
        self.assertFalse(os.path.exists(os.path.join(BACKUPS_DIR, "backup_test.tar")))
        with open(SERVICE_LOG_FILE) as f:
            self.assertIn("Error", f.read())

    def test_create_backup_rejects_path_traversal_name(self):
        os.makedirs("testing", exist_ok=True)
        result = backup.create_backup("testing", "../evil")
        self.assertFalse(result)
        self.assertFalse(os.path.exists("evil.tar"))
        with open(SERVICE_LOG_FILE) as f:
            self.assertIn("Error: rejected unsafe backup name", f.read())


class TestLogging(DaemonTestCase):
    def test_log_format(self):
        from cli.logger import log
        log("Service started", SERVICE_LOG_FILE)
        with open(SERVICE_LOG_FILE) as f:
            line = f.read().strip()
        self.assertRegex(line, r"^\[\d{2}/\d{2}/\d{4} \d{2}:\d{2}\] Service started$")


class TestConstantsAndSourceQuality(unittest.TestCase):
    def test_sleep_constant_is_45_seconds(self):
        self.assertEqual(SERVICE_SLEEP_SECONDS, 45)

    def test_source_uses_try_except(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        relative_paths = (
            os.path.join("daemon", "service.py"),
            os.path.join("daemon", "backup.py"),
            os.path.join("daemon", "schedule_reader.py"),
            os.path.join("daemon", "pid.py"),
        )
        for relative_path in relative_paths:
            with open(os.path.join(root, relative_path)) as f:
                source = f.read()
            self.assertIn("try:", source)
            self.assertIn("except", source)


if __name__ == "__main__":
    unittest.main()
