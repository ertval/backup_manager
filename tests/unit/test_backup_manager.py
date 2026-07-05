import os
import re
import signal
import sys
import tarfile
import tempfile
import unittest
from io import StringIO
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backup_manager import cmd_create, cmd_delete
from cli.backup import do_backup, list_backups
from cli.logger import log
from cli.schedule import add_schedule, list_schedules, remove_schedule
from cli.service import start_service, stop_service
from cli.utils import is_safe_path, is_valid_name, parse_time


# ---------------------------------------------------------------------------
# parse_time
# ---------------------------------------------------------------------------

class TestParseTime(unittest.TestCase):

    def test_valid_colon_format(self):
        self.assertEqual(parse_time("16:00"), ("16", "00"))

    def test_valid_space_format(self):
        self.assertEqual(parse_time("16 00"), ("16", "00"))

    def test_valid_hour_only(self):
        self.assertEqual(parse_time("16"), ("16", "00"))

    def test_valid_zero(self):
        self.assertEqual(parse_time("0"), ("00", "00"))

    def test_valid_single_digit_pads(self):
        self.assertEqual(parse_time("9:05"), ("09", "05"))

    def test_valid_max_time(self):
        self.assertEqual(parse_time("23:59"), ("23", "59"))

    def test_invalid_hour_too_high(self):
        self.assertIsNone(parse_time("24:00"))

    def test_invalid_minute_too_high(self):
        self.assertIsNone(parse_time("16:60"))

    def test_invalid_letters(self):
        self.assertIsNone(parse_time("abc"))

    def test_invalid_negative_hour(self):
        self.assertIsNone(parse_time("-1:00"))

    def test_empty_string(self):
        self.assertIsNone(parse_time(""))


# ---------------------------------------------------------------------------
# is_valid_name
# ---------------------------------------------------------------------------

class TestIsValidName(unittest.TestCase):

    def test_valid_alphanumeric(self):
        self.assertTrue(is_valid_name("mybackup"))

    def test_valid_underscore(self):
        self.assertTrue(is_valid_name("my_backup"))

    def test_valid_dash(self):
        self.assertTrue(is_valid_name("my-backup"))

    def test_valid_mixed(self):
        self.assertTrue(is_valid_name("My-backup_2"))

    def test_invalid_path_traversal(self):
        self.assertFalse(is_valid_name("../../etc/evil"))

    def test_invalid_slash(self):
        self.assertFalse(is_valid_name("backup/test"))

    def test_invalid_space(self):
        self.assertFalse(is_valid_name("backup name"))

    def test_invalid_empty(self):
        self.assertFalse(is_valid_name(""))


# ---------------------------------------------------------------------------
# is_safe_path
# ---------------------------------------------------------------------------

class TestIsSafePath(unittest.TestCase):

    def test_valid_simple(self):
        self.assertTrue(is_safe_path("testingkek"))

    def test_valid_nested(self):
        self.assertTrue(is_safe_path("folder/subfolder"))

    def test_valid_relative_dot(self):
        self.assertTrue(is_safe_path("./testingkek"))

    def test_invalid_parent_traversal(self):
        self.assertFalse(is_safe_path("../etc"))

    def test_invalid_deep_traversal(self):
        self.assertFalse(is_safe_path("../../etc/passwd"))

    def test_invalid_embedded_traversal(self):
        self.assertFalse(is_safe_path("folder/../../etc"))

    def test_invalid_absolute_path(self):
        self.assertFalse(is_safe_path("/etc/passwd"))
        self.assertFalse(is_safe_path("/var/log"))



# ---------------------------------------------------------------------------
# add_schedule
# ---------------------------------------------------------------------------

class TestAddSchedule(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.schedules_file = os.path.join(self.tmp.name, "backup_schedules.txt")

    def tearDown(self):
        self.tmp.cleanup()

    def test_writes_line_to_file(self):
        with patch('cli.schedule.SCHEDULES_FILE', self.schedules_file), \
             patch('cli.schedule.log'):
            add_schedule("testingkek;16:00;mybackup")
        with open(self.schedules_file) as f:
            self.assertIn("testingkek;16:00;mybackup", f.read())

    def test_logs_new_schedule_added(self):
        with patch('cli.schedule.SCHEDULES_FILE', self.schedules_file), \
             patch('cli.schedule.log') as mock_log:
            add_schedule("testingkek;16:00;mybackup")
        mock_log.assert_called_with("New schedule added: testingkek;16:00;mybackup")

    def test_appends_multiple_schedules(self):
        with patch('cli.schedule.SCHEDULES_FILE', self.schedules_file), \
             patch('cli.schedule.log'):
            add_schedule("path1;10:00;a")
            add_schedule("path2;11:00;b")
        with open(self.schedules_file) as f:
            lines = [l.strip() for l in f if l.strip()]
        self.assertEqual(lines, ["path1;10:00;a", "path2;11:00;b"])


# ---------------------------------------------------------------------------
# remove_schedule
# ---------------------------------------------------------------------------

class TestRemoveSchedule(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.schedules_file = os.path.join(self.tmp.name, "backup_schedules.txt")
        with open(self.schedules_file, "w") as f:
            f.write("path1;16:00;backup1\npath2;17:00;backup2\npath3;18:00;backup3\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_removes_correct_line(self):
        with patch('cli.schedule.SCHEDULES_FILE', self.schedules_file), \
             patch('cli.schedule.log'):
            result = remove_schedule(1)
        self.assertTrue(result)
        with open(self.schedules_file) as f:
            lines = [l.strip() for l in f if l.strip()]
        self.assertEqual(lines, ["path1;16:00;backup1", "path3;18:00;backup3"])

    def test_reindexes_after_deletion(self):
        with patch('cli.schedule.SCHEDULES_FILE', self.schedules_file), \
             patch('cli.schedule.log'):
            remove_schedule(0)
        with open(self.schedules_file) as f:
            lines = [l.strip() for l in f if l.strip()]
        self.assertEqual(lines[0], "path2;17:00;backup2")

    def test_logs_deleted(self):
        with patch('cli.schedule.SCHEDULES_FILE', self.schedules_file), \
             patch('cli.schedule.log') as mock_log:
            remove_schedule(0)
        mock_log.assert_called_with("Schedule at index 0 deleted")

    def test_invalid_index_returns_false(self):
        with patch('cli.schedule.SCHEDULES_FILE', self.schedules_file), \
             patch('cli.schedule.log'):
            result = remove_schedule(99)
        self.assertFalse(result)

    def test_invalid_index_logs_error(self):
        with patch('cli.schedule.SCHEDULES_FILE', self.schedules_file), \
             patch('cli.schedule.log') as mock_log:
            remove_schedule(99)
        mock_log.assert_called_with("Error: can't find schedule at index 99")

    def test_missing_file_returns_false(self):
        with patch('cli.schedule.SCHEDULES_FILE', "/nonexistent/schedules.txt"), \
             patch('cli.schedule.log'):
            result = remove_schedule(0)
        self.assertFalse(result)

    def test_missing_file_logs_error(self):
        with patch('cli.schedule.SCHEDULES_FILE', "/nonexistent/schedules.txt"), \
             patch('cli.schedule.log') as mock_log:
            remove_schedule(0)
        mock_log.assert_called_with("Error: can't find backup_schedules.txt")


# ---------------------------------------------------------------------------
# list_schedules
# ---------------------------------------------------------------------------

class TestListSchedules(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.schedules_file = os.path.join(self.tmp.name, "backup_schedules.txt")

    def tearDown(self):
        self.tmp.cleanup()

    def test_prints_zero_indexed_entries(self):
        with open(self.schedules_file, "w") as f:
            f.write("path1;16:00;backup1\npath2;17:00;backup2\n")
        with patch('cli.schedule.SCHEDULES_FILE', self.schedules_file), \
             patch('cli.schedule.log'), \
             patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            list_schedules()
            output = mock_stdout.getvalue()
        self.assertIn("0: path1;16:00;backup1", output)
        self.assertIn("1: path2;17:00;backup2", output)

    def test_logs_show_backups_list(self):
        with open(self.schedules_file, "w") as f:
            f.write("path1;16:00;backup1\n")
        with patch('cli.schedule.SCHEDULES_FILE', self.schedules_file), \
             patch('cli.schedule.log') as mock_log:
            list_schedules()
        mock_log.assert_called_with("Show schedules list")

    def test_missing_file_logs_error(self):
        with patch('cli.schedule.SCHEDULES_FILE', "/nonexistent/schedules.txt"), \
             patch('cli.schedule.log') as mock_log:
            list_schedules()
        mock_log.assert_called_with("Error: can't find backup_schedules.txt")


# ---------------------------------------------------------------------------
# do_backup
# ---------------------------------------------------------------------------

class TestDoBackup(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.backups_dir = os.path.join(self.tmp.name, "backups")
        self.log_file = os.path.join(self.tmp.name, "test.log")
        self.source_dir = os.path.join(self.tmp.name, "source")
        os.makedirs(self.source_dir)
        open(os.path.join(self.source_dir, "file.txt"), "w").close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_creates_tar_file(self):
        with patch('cli.backup.BACKUPS_DIR', self.backups_dir):
            do_backup(self.source_dir, "mybackup", log_file=self.log_file)
        self.assertTrue(os.path.exists(os.path.join(self.backups_dir, "mybackup.tar")))

    def test_tar_filename_is_exact(self):
        with patch('cli.backup.BACKUPS_DIR', self.backups_dir):
            do_backup(self.source_dir, "mybackup", log_file=self.log_file)
        self.assertEqual(os.listdir(self.backups_dir), ["mybackup.tar"])

    def test_logs_backup_done(self):
        with patch('cli.backup.BACKUPS_DIR', self.backups_dir):
            do_backup(self.source_dir, "mybackup", log_file=self.log_file)
        with open(self.log_file) as f:
            self.assertIn("Backup done for " + self.source_dir + " in backups/mybackup.tar", f.read())

    def test_invalid_name_blocked(self):
        with patch('cli.backup.BACKUPS_DIR', self.backups_dir):
            do_backup(self.source_dir, "../../evil", log_file=self.log_file)
        if os.path.exists(self.backups_dir):
            self.assertEqual([f for f in os.listdir(self.backups_dir) if f.endswith(".tar")], [])
        with open(self.log_file) as f:
            self.assertIn("path traversal attempt blocked", f.read())

    def test_missing_path_logs_error(self):
        with patch('cli.backup.BACKUPS_DIR', self.backups_dir):
            do_backup("/nonexistent/path", "mybackup", log_file=self.log_file)
        with open(self.log_file) as f:
            self.assertIn("Error: folder not found for path", f.read())

    def test_duplicate_backup_overwrites(self):
        with patch('cli.backup.BACKUPS_DIR', self.backups_dir):
            do_backup(self.source_dir, "mybackup", log_file=self.log_file)
            do_backup(self.source_dir, "mybackup", log_file=self.log_file)
        with open(self.log_file) as f:
            self.assertEqual(f.read().count("Backup done for"), 2)


# ---------------------------------------------------------------------------
# list_backups
# ---------------------------------------------------------------------------

class TestListBackups(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.backups_dir = os.path.join(self.tmp.name, "backups")

    def tearDown(self):
        self.tmp.cleanup()

    def test_lists_tar_files(self):
        os.makedirs(self.backups_dir)
        open(os.path.join(self.backups_dir, "backup1.tar"), "w").close()
        open(os.path.join(self.backups_dir, "backup2.tar"), "w").close()
        with patch('cli.backup.BACKUPS_DIR', self.backups_dir), \
             patch('cli.backup.log'), \
             patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            list_backups()
            output = mock_stdout.getvalue()
        self.assertIn("backup1.tar", output)
        self.assertIn("backup2.tar", output)

    def test_logs_show_backups_list(self):
        os.makedirs(self.backups_dir)
        open(os.path.join(self.backups_dir, "backup1.tar"), "w").close()
        with patch('cli.backup.BACKUPS_DIR', self.backups_dir), \
             patch('cli.backup.log') as mock_log:
            list_backups()
        mock_log.assert_called_with("Show backups list")

    def test_missing_directory_logs_error(self):
        with patch('cli.backup.BACKUPS_DIR', "/nonexistent/backups"), \
             patch('cli.backup.log') as mock_log:
            list_backups()
        mock_log.assert_called_with("Error: can't find backups directory")

    def test_does_not_list_non_tar_files(self):
        os.makedirs(self.backups_dir)
        open(os.path.join(self.backups_dir, "notes.txt"), "w").close()
        with patch('cli.backup.BACKUPS_DIR', self.backups_dir), \
             patch('cli.backup.log'), \
             patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            list_backups()
            output = mock_stdout.getvalue()
        self.assertNotIn("notes.txt", output)


# ---------------------------------------------------------------------------
# start_service
# ---------------------------------------------------------------------------

class TestStartService(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pid_file = os.path.join(self.tmp.name, "backup_service.pid")

    def tearDown(self):
        self.tmp.cleanup()

    def _make_mock_proc(self, pid=99999):
        mock_proc = MagicMock()
        mock_proc.pid = pid
        return mock_proc

    def test_spawns_with_new_session(self):
        with patch('cli.service.PID_FILE', self.pid_file), \
             patch('cli.service._read_pid', return_value=None), \
             patch('cli.service.log'), \
             patch('subprocess.Popen', return_value=self._make_mock_proc()) as mock_popen:
            start_service()
        _, kwargs = mock_popen.call_args
        self.assertTrue(kwargs.get('start_new_session'))

    def test_writes_pid_to_file(self):
        with patch('cli.service.PID_FILE', self.pid_file), \
             patch('cli.service._read_pid', return_value=None), \
             patch('cli.service.log'), \
             patch('subprocess.Popen', return_value=self._make_mock_proc(99999)):
            start_service()
        self.assertTrue(os.path.exists(self.pid_file))
        with open(self.pid_file) as f:
            self.assertEqual(f.read().strip(), "99999")

    def test_logs_started(self):
        with patch('cli.service.PID_FILE', self.pid_file), \
             patch('cli.service._read_pid', return_value=None), \
             patch('cli.service.log') as mock_log, \
             patch('subprocess.Popen', return_value=self._make_mock_proc()):
            start_service()
        mock_log.assert_any_call("backup_service started")

    def test_already_running_logs_error(self):
        with patch('cli.service.PID_FILE', self.pid_file), \
             patch('cli.service._read_pid', return_value=12345), \
             patch('cli.service._is_running', return_value=True), \
             patch('cli.service.log') as mock_log:
            start_service()
        mock_log.assert_any_call("Error: backup_service already running")

    def test_already_running_does_not_spawn(self):
        with patch('cli.service.PID_FILE', self.pid_file), \
             patch('cli.service._read_pid', return_value=12345), \
             patch('cli.service._is_running', return_value=True), \
             patch('cli.service.log'), \
             patch('subprocess.Popen') as mock_popen:
            start_service()
        mock_popen.assert_not_called()

    def test_popen_failure_logs_error(self):
        with patch('cli.service.PID_FILE', self.pid_file), \
             patch('cli.service._read_pid', return_value=None), \
             patch('cli.service.log') as mock_log, \
             patch('subprocess.Popen', side_effect=Exception("spawn error")):
            start_service()
        mock_log.assert_called_with("Error: can't start backup_service: spawn error")



# ---------------------------------------------------------------------------
# stop_service
# ---------------------------------------------------------------------------

class TestStopService(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pid_file = os.path.join(self.tmp.name, "backup_service.pid")
        with open(self.pid_file, "w") as f:
            f.write("12345")

    def tearDown(self):
        self.tmp.cleanup()

    def test_sends_sigterm(self):
        with patch('cli.service.PID_FILE', self.pid_file), \
             patch('cli.service._read_pid', return_value=12345), \
             patch('cli.service._is_running', return_value=True), \
             patch('cli.service.log'), \
             patch('os.kill') as mock_kill:
            stop_service()
        mock_kill.assert_called_once_with(12345, signal.SIGTERM)

    def test_removes_pid_file(self):
        with patch('cli.service.PID_FILE', self.pid_file), \
             patch('cli.service._read_pid', return_value=12345), \
             patch('cli.service._is_running', return_value=True), \
             patch('cli.service.log'), \
             patch('os.kill'):
            stop_service()
        self.assertFalse(os.path.exists(self.pid_file))

    def test_logs_stopped(self):
        with patch('cli.service.PID_FILE', self.pid_file), \
             patch('cli.service._read_pid', return_value=12345), \
             patch('cli.service._is_running', return_value=True), \
             patch('cli.service.log') as mock_log, \
             patch('os.kill'):
            stop_service()
        mock_log.assert_any_call("backup_service stopped")

    def test_not_running_logs_error(self):
        with patch('cli.service.PID_FILE', self.pid_file), \
             patch('cli.service._read_pid', return_value=None), \
             patch('cli.service.log') as mock_log:
            stop_service()
        mock_log.assert_called_with("Error: can't stop backup_service")

    def test_not_running_does_not_kill(self):
        with patch('cli.service.PID_FILE', self.pid_file), \
             patch('cli.service._read_pid', return_value=None), \
             patch('cli.service.log'), \
             patch('os.kill') as mock_kill:
            stop_service()
        mock_kill.assert_not_called()

    def test_kill_failure_logs_error(self):
        with patch('cli.service.PID_FILE', self.pid_file), \
             patch('cli.service._read_pid', return_value=12345), \
             patch('cli.service._is_running', return_value=True), \
             patch('cli.service.log') as mock_log, \
             patch('os.kill', side_effect=Exception("kill error")):
            stop_service()
        mock_log.assert_called_with("Error: can't stop backup_service: kill error")



# ---------------------------------------------------------------------------
# cmd_create (argument-mode routing in backup_manager.py)
# ---------------------------------------------------------------------------

class TestCmdCreate(unittest.TestCase):

    def test_valid_schedule_calls_add_schedule(self):
        with patch('backup_manager.add_schedule') as mock_add, \
             patch('backup_manager.log'):
            cmd_create("testingkek;16:00;mybackup")
        mock_add.assert_called_once_with("testingkek;16:00;mybackup")

    def test_normalises_time_before_saving(self):
        with patch('backup_manager.add_schedule') as mock_add, \
             patch('backup_manager.log'):
            cmd_create("testingkek;9:5;mybackup")
        mock_add.assert_called_once_with("testingkek;09:05;mybackup")

    def test_malformed_missing_parts_logs_error(self):
        with patch('backup_manager.add_schedule'), \
             patch('backup_manager.log') as mock_log:
            cmd_create("wrong_format")
        mock_log.assert_called_with("Error: malformed schedule: wrong_format")

    def test_malformed_empty_path_logs_error(self):
        with patch('backup_manager.add_schedule'), \
             patch('backup_manager.log') as mock_log:
            cmd_create(";16:00;mybackup")
        mock_log.assert_called_with("Error: malformed schedule: ;16:00;mybackup")

    def test_invalid_time_logs_error(self):
        with patch('backup_manager.add_schedule'), \
             patch('backup_manager.log') as mock_log:
            cmd_create("testingkek;99:99;mybackup")
        mock_log.assert_called_with("Error: malformed schedule: testingkek;99:99;mybackup")

    def test_unsafe_path_logs_error(self):
        with patch('backup_manager.add_schedule'), \
             patch('backup_manager.log') as mock_log:
            cmd_create("../etc/passwd;16:00;mybackup")
        mock_log.assert_called_with("Error: malformed schedule: ../etc/passwd;16:00;mybackup")

    def test_invalid_name_logs_error(self):
        with patch('backup_manager.add_schedule'), \
             patch('backup_manager.log') as mock_log:
            cmd_create("testingkek;16:00;bad name!")
        mock_log.assert_called_with("Error: malformed schedule: testingkek;16:00;bad name!")


# ---------------------------------------------------------------------------
# cmd_delete (argument-mode routing in backup_manager.py)
# ---------------------------------------------------------------------------

class TestCmdDelete(unittest.TestCase):

    def test_valid_index_calls_remove_schedule(self):
        with patch('backup_manager.remove_schedule') as mock_rm, \
             patch('backup_manager.log'):
            cmd_delete("2")
        mock_rm.assert_called_once_with(2)

    def test_non_numeric_index_logs_error(self):
        with patch('backup_manager.remove_schedule'), \
             patch('backup_manager.log') as mock_log:
            cmd_delete("abc")
        mock_log.assert_called_with("Error: can't find schedule at index abc")

    def test_non_numeric_does_not_call_remove(self):
        with patch('backup_manager.remove_schedule') as mock_rm, \
             patch('backup_manager.log'):
            cmd_delete("abc")
        mock_rm.assert_not_called()


# ---------------------------------------------------------------------------
# Log format
# ---------------------------------------------------------------------------

class TestLogFormat(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log_file = os.path.join(self.tmp.name, "test.log")

    def tearDown(self):
        self.tmp.cleanup()

    def test_format_matches_spec(self):
        log("Test message", log_file=self.log_file)
        with open(self.log_file) as f:
            line = f.read().strip()
        pattern = r'^\[\d{2}/\d{2}/\d{4} \d{2}:\d{2}\] .+$'
        self.assertRegex(line, pattern, f"Log line does not match [dd/mm/yyyy hh:mm] format: {line!r}")

    def test_message_preserved(self):
        log("Hello world", log_file=self.log_file)
        with open(self.log_file) as f:
            self.assertIn("Hello world", f.read())


# ---------------------------------------------------------------------------
# try/except coverage in source files
# ---------------------------------------------------------------------------

class TestTryExceptInSource(unittest.TestCase):

    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    def _assert_has_try_except(self, rel_path):
        full = os.path.join(self.ROOT, rel_path)
        with open(full) as f:
            src = f.read()
        self.assertIn("try:", src, f"'try:' not found in {rel_path}")
        self.assertIn("except", src, f"'except' not found in {rel_path}")

    def test_cli_backup(self):
        self._assert_has_try_except(os.path.join("cli", "backup.py"))

    def test_cli_schedule(self):
        self._assert_has_try_except(os.path.join("cli", "schedule.py"))

    def test_cli_service(self):
        self._assert_has_try_except(os.path.join("cli", "service.py"))

    def test_cli_utils(self):
        self._assert_has_try_except(os.path.join("cli", "utils.py"))

    def test_cli_logger(self):
        self._assert_has_try_except(os.path.join("cli", "logger.py"))


if __name__ == "__main__":
    unittest.main()
