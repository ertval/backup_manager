#!/bin/bash

# Exit on error
set -e

echo "=== Starting Backup Manager Demo ==="

# 1. Setup fast sleep dynamically for demo
CONFIG_FILE="cli/config.py"
sed -i.bak 's/SERVICE_SLEEP_SECONDS = 45/SERVICE_SLEEP_SECONDS = 1/g' "$CONFIG_FILE"

# Cleanup function to restore config even if script fails
cleanup() {
    echo "=== Cleaning up config ==="
    if [ -f "${CONFIG_FILE}.bak" ]; then
        mv "${CONFIG_FILE}.bak" "$CONFIG_FILE"
    fi
}
trap cleanup EXIT

# 2. Reset environment
echo "--> Cleaning logs, backups, and schedules..."
rm -rf logs backups backup_schedules.txt

# 3. Create test-folder if missing
mkdir -p test-folder
echo "faaaaaaaaaaaaah" > test-folder/rou.txt

# 4. Create schedule at current time
HH_MM=$(date +"%H:%M")
echo "--> Creating backup schedule for test-folder at $HH_MM..."
python3 ./backup_manager.py create "test-folder;${HH_MM};demo_backup"

# 5. Start background daemon
echo "--> Starting daemon..."
python3 ./backup_manager.py start

# 6. Wait for backup to be created (max 5 seconds)
echo "--> Waiting for backup to trigger..."
for i in {1..5}; do
    if [ -f "backups/demo_backup.tar" ]; then
        echo "--> Backup found!"
        break
    fi
    sleep 1
done

# 7. Stop the daemon
echo "--> Stopping daemon..."
python3 ./backup_manager.py stop

# 8. Display results
echo ""
echo "=== DEMO RESULTS ==="
echo "--> Directory contents:"
ls -F

echo ""
echo "--> Schedule file (backup_schedules.txt):"
cat backup_schedules.txt || echo "[File deleted or not found]"

echo ""
echo "--> Backup directory (backups/):"
ls -la backups/

echo ""
echo "--> Backup archive contents (tar -tvf):"
tar -tvf backups/demo_backup.tar

echo ""
echo "--> CLI logs (logs/backup_manager.log):"
cat logs/backup_manager.log

echo ""
echo "--> Service logs (logs/backup_service.log):"
cat logs/backup_service.log

echo "=== Demo Finished successfully ==="
