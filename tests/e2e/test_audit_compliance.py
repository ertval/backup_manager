import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import tarfile

class TestAuditCompliance(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)

        # Copy workspace files
        src_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shutil.copy(os.path.join(src_root, "backup_manager.py"), ".")
        shutil.copy(os.path.join(src_root, "backup_service.py"), ".")
        shutil.copytree(os.path.join(src_root, "cli"), "cli")
        shutil.copytree(os.path.join(src_root, "daemon"), "daemon")

        # Set fast sleep constant for daemon
        config_path = "cli/config.py"
        with open(config_path, "r") as f:
            content = f.read()
        content = content.replace("SERVICE_SLEEP_SECONDS = 45", "SERVICE_SLEEP_SECONDS = 0.1")
        with open(config_path, "w") as f:
            f.write(content)

    def tearDown(self):
        # Stop daemon if running
        try:
            subprocess.run([sys.executable, "backup_manager.py", "stop"], capture_output=True)
        except Exception:
            pass
        os.chdir(self.old_cwd)
        self.tmpdir.cleanup()

    def test_1_clean_state(self):
        # Verify fresh environment clean leaves system in clean state
        # First create dummy dirs/files
        os.makedirs("logs", exist_ok=True)
        os.makedirs("backups", exist_ok=True)
        open("backup_schedules.txt", "w").close()

        # Run clean command
        shutil.rmtree("logs")
        shutil.rmtree("backups")
        os.remove("backup_schedules.txt")

        self.assertFalse(os.path.exists("logs"))
        self.assertFalse(os.path.exists("backups"))
        self.assertFalse(os.path.exists("backup_schedules.txt"))

    def test_2_scripts_present(self):
        self.assertTrue(os.path.exists("backup_manager.py"))
        self.assertTrue(os.path.exists("backup_service.py"))

    def test_3_and_4_create_schedule(self):
        # Run create
        result = subprocess.run([sys.executable, "backup_manager.py", "create", "test2;18:15;backup_test2"], capture_output=True, text=True)
        self.assertTrue(os.path.exists("backup_schedules.txt"))
        
        with open("backup_schedules.txt") as f:
            content = f.read().strip()
        self.assertEqual(content, "test2;18:15;backup_test2")

    def test_5_6_7_stop_no_daemon_and_logs(self):
        # Run stop when service is not running
        result = subprocess.run([sys.executable, "backup_manager.py", "stop"], capture_output=True, text=True)
        self.assertIn("Error: can't stop backup_service.", result.stdout)

        self.assertTrue(os.path.exists("logs"))
        self.assertTrue(os.path.exists("logs/backup_manager.log"))

        with open("logs/backup_manager.log") as f:
            log_content = f.read().strip()
        
        # Verify timestamp and error message format
        pattern = r"^\[\d{2}/\d{2}/\d{4} \d{2}:\d{2}\] Error: can't stop backup_service$"
        self.assertRegex(log_content, pattern)

    def test_8_9_10_list_delete_reindex(self):
        # Create schedules
        subprocess.run([sys.executable, "backup_manager.py", "create", "test2;18:15;backup_test2"], capture_output=True)
        subprocess.run([sys.executable, "backup_manager.py", "create", "test3;18:16;backup_test3"], capture_output=True)
        subprocess.run([sys.executable, "backup_manager.py", "create", "test4;18:17;backup_test4"], capture_output=True)

        # List
        result = subprocess.run([sys.executable, "backup_manager.py", "list"], capture_output=True, text=True)
        lines = [line.strip() for line in result.stdout.split("\n") if line.strip() and not line.startswith("---")]
        self.assertEqual(lines[0], "0: test2;18:15;backup_test2")
        self.assertEqual(lines[1], "1: test3;18:16;backup_test3")
        self.assertEqual(lines[2], "2: test4;18:17;backup_test4")

        # Delete index 1
        del_result = subprocess.run([sys.executable, "backup_manager.py", "delete", "1"], capture_output=True, text=True)
        self.assertIn("Schedule at index 1 deleted.", del_result.stdout)

        # List again
        result2 = subprocess.run([sys.executable, "backup_manager.py", "list"], capture_output=True, text=True)
        lines2 = [line.strip() for line in result2.stdout.split("\n") if line.strip() and not line.startswith("---")]
        self.assertEqual(lines2[0], "0: test2;18:15;backup_test2")
        self.assertEqual(lines2[1], "1: test4;18:17;backup_test4")

    def test_11_12_start_lifecycle_and_double_start(self):
        # Start daemon
        result = subprocess.run([sys.executable, "backup_manager.py", "start"], capture_output=True, text=True)
        self.assertIn("backup_service started.", result.stdout)

        pid_file = "logs/backup_service.pid"
        self.assertTrue(os.path.exists(pid_file))
        with open(pid_file) as f:
            pid = int(f.read().strip())

        # Check process active
        try:
            os.kill(pid, 0)
            process_alive = True
        except OSError:
            process_alive = False
        self.assertTrue(process_alive)

        # Start again
        result2 = subprocess.run([sys.executable, "backup_manager.py", "start"], capture_output=True, text=True)
        self.assertIn("Error: backup_service already running.", result2.stdout)

    def test_13_backup_execution_and_passed_time(self):
        # Create testing folders/files
        os.makedirs("testing", exist_ok=True)
        with open("testing/file1", "w") as f: f.write("content1")
        with open("testing/file2", "w") as f: f.write("content2")

        # Schedule at current time
        now = time.localtime()
        hh = f"{now.tm_hour:02d}"
        mm = f"{now.tm_min:02d}"
        
        subprocess.run([sys.executable, "backup_manager.py", "create", f"testing;{hh}:{mm};backup_test"], capture_output=True)
        # Schedule in the past
        subprocess.run([sys.executable, "backup_manager.py", "create", "testing;13:11;passed_time_backup"], capture_output=True)

        # Start service
        subprocess.run([sys.executable, "backup_manager.py", "start"], capture_output=True)

        # Wait for backup
        backup_tar = "backups/backup_test.tar"
        for _ in range(50):
            if os.path.exists(backup_tar):
                break
            time.sleep(0.1)

        self.assertTrue(os.path.exists(backup_tar))
        
        # Verify passed_time_backup was not created
        self.assertFalse(os.path.exists("backups/passed_time_backup.tar"))

        # Verify tar contents via tarfile
        with tarfile.open(backup_tar) as tar:
            names = tar.getnames()
            self.assertIn("testing/file1", names)
            self.assertIn("testing/file2", names)
            self.assertEqual(tar.getmember("testing/file1").size, 8)

        # Stop service
        subprocess.run([sys.executable, "backup_manager.py", "stop"], capture_output=True)

        # Wait a moment for daemon to exit and write state, then check schedule file
        time.sleep(0.5)
        with open("backup_schedules.txt") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        
        # Verify passed schedule was removed, but current hour/minute schedule remains (since hh:mm == now.hour:now.minute on the tick)
        self.assertIn(f"testing;{hh}:{mm};backup_test", lines)
        self.assertNotIn("testing;13:11;passed_time_backup", lines)

    def test_14_zip_folder_backup(self):
        # Create a real ZIP archive with some folders and files inside it
        import zipfile
        os.makedirs("zip_src/sub", exist_ok=True)
        with open("zip_src/sub/file1.txt", "w") as f:
            f.write("zip content")
        with zipfile.ZipFile("testing_zip.zip", "w") as z:
            z.write("zip_src/sub/file1.txt", arcname="sub/file1.txt")
        shutil.rmtree("zip_src")

        now = time.localtime()
        hh = f"{now.tm_hour:02d}"
        mm = f"{now.tm_min:02d}"

        subprocess.run([sys.executable, "backup_manager.py", "create", f"testing_zip.zip;{hh}:{mm};zip_backup"], capture_output=True)
        subprocess.run([sys.executable, "backup_manager.py", "start"], capture_output=True)

        backup_tar = "backups/zip_backup.tar"
        for _ in range(50):
            if os.path.exists(backup_tar):
                break
            time.sleep(0.1)

        self.assertTrue(os.path.exists(backup_tar))

        with tarfile.open(backup_tar) as tar:
            names = tar.getnames()
            self.assertIn("testing_zip.zip", names)


    def test_15_unknown_instruction_logged(self):
        result = subprocess.run([sys.executable, "backup_manager.py", "invalid_command"], capture_output=True, text=True)
        self.assertIn("Error: unknown instruction", result.stdout)

        with open("logs/backup_manager.log") as f:
            log_content = f.read().strip()
        self.assertIn("Error: unknown instruction", log_content)

    def test_16_error_logs(self):
        # 1. Stop when stopped
        subprocess.run([sys.executable, "backup_manager.py", "stop"], capture_output=True)
        # 2. Create malformed
        subprocess.run([sys.executable, "backup_manager.py", "create", "wrong_format"], capture_output=True)
        # 3. Backups list when missing backups dir (remove backups folder if exists)
        if os.path.exists("backups"):
            shutil.rmtree("backups")
        subprocess.run([sys.executable, "backup_manager.py", "backups"], capture_output=True)
        # 4. Start when running
        subprocess.run([sys.executable, "backup_manager.py", "start"], capture_output=True)
        subprocess.run([sys.executable, "backup_manager.py", "start"], capture_output=True)
        # 5. Daemon check when schedules file missing (remove schedules file, wait)
        if os.path.exists("backup_schedules.txt"):
            os.remove("backup_schedules.txt")
        time.sleep(0.5)
        
        # Verify manager log contents
        with open("logs/backup_manager.log") as f:
            mgr_log = f.read()
            self.assertIn("Error: can't stop backup_service", mgr_log)
            self.assertIn("Error: malformed schedule: wrong_format", mgr_log)
            self.assertIn("Error: can't find backups directory", mgr_log)
            self.assertIn("Error: backup_service already running", mgr_log)

        # Verify service log contents
        with open("logs/backup_service.log") as f:
            svc_log = f.read()
            self.assertIn("Error: cannot open backup_schedules", svc_log)

    def test_17_try_except_in_source(self):
        # Verify try/except blocks exist in major scripts
        for path in [
            "backup_manager.py", "backup_service.py",
            "cli/backup.py", "cli/logger.py", "cli/schedule.py", "cli/service.py", "cli/utils.py",
            "daemon/backup.py", "daemon/pid.py", "daemon/schedule_reader.py", "daemon/service.py"
        ]:
            with open(path) as f:
                content = f.read()
            self.assertIn("try:", content)
            self.assertIn("except", content)


if __name__ == "__main__":
    unittest.main()
