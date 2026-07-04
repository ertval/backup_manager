import os
import re
import tarfile
import tempfile
import unittest
from datetime import datetime

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
        service.run_cycle(set(), now=now)

        self.assertFalse(os.path.exists(os.path.join(BACKUPS_DIR, "passed_time_backup.tar")))


class TestDeduplication(DaemonTestCase):
    def test_same_schedule_not_triggered_twice_same_day(self):
        os.makedirs("testing", exist_ok=True)
        with open("backup_schedules.txt", "w") as f:
            f.write("testing;18:21;backup_test\n")

        now = datetime(2026, 7, 4, 18, 21)
        executed = set()
        service.run_cycle(executed, now=now)
        service.run_cycle(executed, now=now)

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
        service.run_cycle(executed, now=day1)
        service.run_cycle(executed, now=day2)

        with open(SERVICE_LOG_FILE) as f:
            occurrences = f.read().count("Backup done for testing in backups/backup_test.tar")
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
