# 🗄️ Backup Manager

> **Zero-dependency backup scheduling** — pure Python 3, Unix/Linux.

A CLI-driven daemon that schedules, tracks, and compresses folder backups. Built entirely with Python's standard library — no `pip install` required.

---

## ✨ Features

| | |
|---|---|
| 🎮 **CLI Schedule Management** | Create, list, delete backup tasks in seconds |
| ⚙️ **Background Daemon** | Auto-executes daily backups with zero supervision |
| 🔒 **PID Locking** | Prevents duplicate daemon instances via `backup_service.pid` |
| 📦 **Tar Archives** | Compresses target folders to `.tar` with full hierarchy preserved |
| 📋 **Timestamped Logs** | Structured `[dd/mm/yyyy hh:mm]` logging for both CLI and daemon |
| 🧪 **Fully Tested** | Unit + integration + E2E audit tests using `unittest` |

---

## 📁 Directory Structure

```
backup_manager/
├── 📁 cli/                   # Modular CLI application logic
│   ├── 🐍 backup.py          # Backup creation & interactive trigger
│   ├── 🐍 config.py          # Path and sleep configuration constants
│   ├── 🐍 logger.py          # Standard log writing utility
│   ├── 🐍 menu.py            # Main menu CLI interactive dashboard
│   ├── 🐍 schedule.py        # Schedule manager (add/remove/list)
│   ├── 🐍 service.py         # Subprocess controllers for daemon lifecycle
│   └── 🐍 utils.py           # Parsing and path traversal verification
├── 📁 daemon/                # Background daemon process logic
│   ├── 🐍 backup.py          # Safety checks wrapper for daemon backups
│   ├── 🐍 pid.py             # Daemon process ID registration
│   ├── 🐍 schedule_reader.py # Schedule loader & validator
│   └── 🐍 service.py         # Daemon event loop
├── 📚 docs/                  # QA checklists, requirements, & reports
│   ├── audit.md              # E2E compliance validation checks
│   ├── development_plan.md   # Architectural mapping & test specs
│   ├── readme.md             # Functional requirements manual
│   ├── requirements.md       # Technical contracts & constraints
│   └── 📁 reports/           # Security audit reports
├── 🧪 tests/                 # Built-in unit/integration/E2E test suite
│   ├── unit/                 # Unit tests (Dev 2 & 3)
│   ├── integration/          # CLI-daemon interprocess communication tests
│   └── e2e/                  # Audit checklist validation
├── 🧠 AGENTS.md              # Coding guidelines & mandates
├── 🐍 backup_manager.py      # Entry point executable
├── 🐍 backup_service.py      # Background daemon entry point
├── 📄 backup_schedules.txt   # Schedule storage (created at runtime)
├── 📂 logs/                  # Diagnostics directory (created at runtime)
│   ├── backup_manager.log    # CLI diagnostic log
│   ├── backup_service.log    # Daemon diagnostic log
│   └── backup_service.pid    # Running daemon process ID locking file
└── 📦 backups/               # Backup archives directory (created at runtime)
    └── *.tar                 # Generated archives
```

---

## 🚀 Running the Project

### 🎬 Automated Demo Mode
Run the automated pipeline to see schedules, daemon execution, manual logs, and duplicate checking in a single command:
```bash
./run_demo.sh
```
Or run using Makefile:
```bash
make demo
```

### 🎮 Interactive Mode
Run the tool without arguments to access the interactive dashboard menu:
```bash
python3 ./backup_manager.py
```
This lets you manually run backups, add/delete schedules, view backups, and control the daemon.

### 💻 Argument Mode
Run instructions directly from the terminal:
```bash
python3 ./backup_manager.py <command> [argument]
```

### Commands

| Command | Argument | Description |
|:---|:---|:---|
| `start` | — | Spawns `backup_service.py` in the background |
| `stop` | — | Kills the active daemon and cleans up PID file |
| `create` | `"path;hh:mm;name"` | Adds a backup schedule |
| `list` | — | Prints schedules with 0-based index |
| `delete` | `[index]` | Removes schedule at given index |
| `backups` | — | Lists generated `.tar` files in `./backups` |

---

## 🎯 Walkthrough

### 1. 📝 Create Schedules

```bash
$ python3 ./backup_manager.py create "testing;18:21;backup_test"
$ python3 ./backup_manager.py create "testing2;13:11;passed_time_backup"
```

### 2. 📋 List Schedules

```bash
$ python3 ./backup_manager.py list
0: testing;18:21;backup_test
1: testing2;13:11;passed_time_backup
```

### 3. 🗑️ Delete a Schedule

```bash
$ python3 ./backup_manager.py delete 1
$ python3 ./backup_manager.py list
0: testing;18:21;backup_test    # Index 2 → 1 after re-indexing
```

### 4. ▶️ Start / ⏹️ Stop Daemon

```bash
$ python3 ./backup_manager.py start
$ python3 ./backup_manager.py stop
```

### 5. 📜 Review Logs

**CLI & Manual Backups** (`./logs/backup_manager.log`):
```text
[03/07/2026 18:21] New schedule added: testing;18:21;backup_test
[03/07/2026 18:21] Error: malformed schedule: wrong_format
[03/07/2026 18:21] backup_service started
[03/07/2026 18:22] Manual backup done for testing in backups/mybackup.tar
```

**Daemon** (`./logs/backup_service.log`):
```text
[03/07/2026 18:21] Backup done for testing in backups/backup_test.tar
[03/07/2026 18:22] Error: backup 'roufa_04-07-2026_18:21.tar' already exists, skipping
[03/07/2026 18:23] Error: folder not found for path: missing_folder
```

---

## 🏗️ Architecture

### 🔐 Process Lifecycle (PID File)

```
start → check backup_service.pid
         ├── exists & active → ❌ log "already running" → abort
         └── missing/dead    → ✅ spawn daemon → write PID → log "started"

stop  → read backup_service.pid
         ├── exists & active → ✅ SIGTERM → clean PID → log "stopped"
         └── missing/dead    → ❌ log "can't stop" → abort
```

### 🔄 Daemon Loop

```
while True:
    1. Read backup_schedules.txt
    2. For each schedule:
       ├── time matches now?       → create .tar → log
       ├── time already passed?    → skip
       └── already ran today?      → skip (dedup)
    3. Sleep 45 seconds 🥱
```

### 📦 Archive Safety

Backups are standard `.tar` files. Verify integrity anytime:

```bash
tar -tvf ./backups/backup_test.tar
```

---

## 🧪 Testing

All tests use Python's built-in `unittest` — **zero external dependencies**. Shorter commands are available via the `Makefile`.

### Test Layout

```
tests/
├── 🔬 unit/           # Unit tests (CLI & daemon operations)
├── 🔗 integration/    # CLI ↔ daemon interprocess execution tests
└── ✅ e2e/            # End-to-end audit compliance verification
```

### Run Tests

```bash
make test             # 🎯 Run all tests
make test-unit        # 🔬 Run unit tests only
make test-integration # 🔗 Run integration tests only
make test-e2e         # ✅ Run E2E audit tests only
```

---

## 🔧 Troubleshooting

| Symptom | Fix |
|:---|---|
| Daemon won't stop | `ps -p $(cat logs/backup_service.pid)` then `kill -15 <PID>` |
| Permission denied | `chmod +x backup_manager.py backup_service.py` |
| Schedule didn't fire | Time already passed today? It triggers tomorrow at the matching hour |
| Duplicate backup warning | Daemon deduplicates by `(date, schedule)` — one per day max |
