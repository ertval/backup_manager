import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import tarfile

class TestCliDaemonIntegration(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)

        # Copy workspace files to temp directory for absolute isolation
        src_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shutil.copy(os.path.join(src_root, "backup_manager.py"), ".")
        shutil.copy(os.path.join(src_root, "backup_service.py"), ".")
        shutil.copytree(os.path.join(src_root, "cli"), "cli")
        shutil.copytree(os.path.join(src_root, "daemon"), "daemon")

        # Speed up daemon loop in config.py by setting sleep to 0.1 seconds
        config_path = "cli/config.py"
        with open(config_path, "r") as f:
            content = f.read()
        content = content.replace("SERVICE_SLEEP_SECONDS = 45", "SERVICE_SLEEP_SECONDS = 0.1")
        with open(config_path, "w") as f:
            f.write(content)

    def tearDown(self):
        # Defensively kill daemon if running
        try:
            subprocess.run([sys.executable, "backup_manager.py", "stop"], capture_output=True)
        except Exception:
            pass
        os.chdir(self.old_cwd)
        self.tmpdir.cleanup()

    def _is_process_alive(self, pid):
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def test_start_spawns_process(self):
        result = subprocess.run([sys.executable, "backup_manager.py", "start"], capture_output=True, text=True)
        self.assertIn("backup_service started.", result.stdout)

        pid_file = "logs/backup_service.pid"
        self.assertTrue(os.path.exists(pid_file))
        with open(pid_file) as f:
            pid = int(f.read().strip())
        
        self.assertTrue(self._is_process_alive(pid))

    def test_stop_terminates_process(self):
        # Start daemon
        subprocess.run([sys.executable, "backup_manager.py", "start"], capture_output=True)
        pid_file = "logs/backup_service.pid"
        self.assertTrue(os.path.exists(pid_file))
        with open(pid_file) as f:
            pid = int(f.read().strip())

        # Stop daemon
        result = subprocess.run([sys.executable, "backup_manager.py", "stop"], capture_output=True, text=True)
        self.assertIn("backup_service stopped.", result.stdout)
        self.assertFalse(os.path.exists(pid_file))
        
        # Wait a moment for process exit
        time.sleep(0.5)
        self.assertFalse(self._is_process_alive(pid))

    def test_double_start_prevention(self):
        # Start daemon
        subprocess.run([sys.executable, "backup_manager.py", "start"], capture_output=True)
        
        # Try to start again
        result = subprocess.run([sys.executable, "backup_manager.py", "start"], capture_output=True, text=True)
        self.assertIn("Error: backup_service already running.", result.stdout)

        # Check logs
        with open("logs/backup_manager.log") as f:
            log_content = f.read()
            self.assertIn("Error: backup_service already running", log_content)

    def test_full_create_start_backup_stop_flow(self):
        # Create testing directory & source files
        os.makedirs("testing", exist_ok=True)
        with open("testing/file1.txt", "w") as f:
            f.write("hello world")

        # Create schedule at current local time
        now = time.localtime()
        hh = f"{now.tm_hour:02d}"
        mm = f"{now.tm_min:02d}"
        schedule_str = f"testing;{hh}:{mm};mybackup"

        # Register schedule
        subprocess.run([sys.executable, "backup_manager.py", "create", schedule_str], capture_output=True)
        
        # Verify schedule file exists
        self.assertTrue(os.path.exists("backup_schedules.txt"))

        # Start daemon
        subprocess.run([sys.executable, "backup_manager.py", "start"], capture_output=True)

        # Wait for backup to be created (fast loop)
        backup_tar = "backups/mybackup.tar"
        for _ in range(50):
            if os.path.exists(backup_tar):
                break
            time.sleep(0.1)

        self.assertTrue(os.path.exists(backup_tar))

        # Verify tar contents
        with tarfile.open(backup_tar) as tar:
            names = tar.getnames()
            self.assertIn("testing/file1.txt", names)

        # Stop daemon
        subprocess.run([sys.executable, "backup_manager.py", "stop"], capture_output=True)

if __name__ == "__main__":
    unittest.main()
