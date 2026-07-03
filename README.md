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
├── 📚 docs/
│   ├── audit.md              # QA verification checklist
│   └── requirements.md       # Technical specification
├── 🧪 tests/
│   ├── unit/                 # Unit tests (Dev 2 & 3)
│   ├── integration/          # CLI ↔ daemon tests (Dev 1)
│   └── e2e/                  # Audit compliance tests (Dev 1)
├── 🧠 AGENTS.md              # Agent coding conventions
├── 🐍 backup_manager.py      # CLI entry point
├── 🐍 backup_service.py      # Background daemon
├── 📄 backup_schedules.txt   # Schedule storage (semicolon-separated)
├── 📂 logs/
│   ├── backup_manager.log    # CLI diagnostics
│   ├── backup_service.log    # Daemon diagnostics
│   └── backup_service.pid    # Active daemon PID
└── 📦 backups/
    └── *.tar                 # Generated archives
```

---

## 🚀 CLI Usage

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

**CLI** (`./logs/backup_manager.log`):
```text
[03/07/2026 18:21] New schedule added: testing;18:21;backup_test
[03/07/2026 18:21] Error: malformed schedule: wrong_format
[03/07/2026 18:21] backup_service started
```

**Daemon** (`./logs/backup_service.log`):
```text
[03/07/2026 18:21] Backup done for testing in backups/backup_test.tar
[03/07/2026 18:22] Error: folder not found for path_to_save: missing_folder
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

All tests use Python's built-in `unittest` — **zero external dependencies**.

### Test Layout

```
tests/
├── 🔬 unit/           # Dev 2 & 3 — gating criteria for Phase 3
├── 🔗 integration/    # Dev 1 — CLI ↔ daemon interaction
└── ✅ e2e/            # Dev 1 — audit.md compliance
```

### Run Tests

```bash
python3 -m unittest discover -s tests -v            # 🎯 all tests
python3 -m unittest discover -s tests/unit -v        # 🔬 unit (phase 2 gate)
python3 -m unittest discover -s tests/integration -v # 🔗 integration
python3 -m unittest discover -s tests/e2e -v         # ✅ E2E audit
```

See [`development_plan.md`](development_plan.md) §5 for the full audit-to-test mapping and coverage requirements.

---

## 🔧 Troubleshooting

| Symptom | Fix |
|:---|---|
| Daemon won't stop | `ps -p $(cat logs/backup_service.pid)` then `kill -15 <PID>` |
| Permission denied | `chmod +x backup_manager.py backup_service.py` |
| Schedule didn't fire | Time already passed today? It triggers tomorrow at the matching hour |
| Duplicate backup warning | Daemon deduplicates by `(date, schedule)` — one per day max |
