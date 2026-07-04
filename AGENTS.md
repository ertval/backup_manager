# Workspace Agent Instructions & Guidelines (AGENTS.md)

Rules, constraints, and conventions for AI agents working on **Backup Manager**.

---

## 1. Core Mandates

1. **Pure Python Standard Library** — no `pip install` dependencies. Use `subprocess`, `signal`, `os`, `tarfile`, `datetime`, `time`, `shlex`.
2. **Defensive Error Handling** — `try`/`except` around all I/O, process spawn/kill, file ops. Unhandled exceptions must never terminate the daemon.
3. **Structured Log Outputs** — events/exceptions to `./logs/{script}.log`. Format: `[dd/mm/yyyy hh:mm] Message`.
4. **State Persistence** — daemon PID in `./logs/backup_service.pid`. Clean up on stop or dead-process detection.
5. **Requirements & Audit Compliance** — see [`docs/requirements.md`](docs/requirements.md) for CLI/daemon specs and error message contracts.
6. **Docs Are Source of Truth** — [`docs/`](docs/) (requirements.md, audit.md, readme.md) are canonical. `development_plan.md`, code, and tests must not contradict them. Where `audit.md` illustrative example outputs differ from canonical spec strings in `requirements.md`/`readme.md`, the canonical spec wins. Resolve any plan↔docs conflict by editing the plan to match docs, never the reverse.

## 2. File Architecture

Key paths agent must know:
- `backup_manager.py` — CLI entry point (Dev 2)
- `backup_service.py` — daemon (Dev 3)
- `backup_schedules.txt` — schedule storage (semicolon-separated)
- `logs/backup_manager.log` — CLI logs
- `logs/backup_service.log` — daemon logs
- `logs/backup_service.pid` — daemon PID file
- `backups/*.tar` — generated archives
- `tests/unit/` — unit tests (Dev 2/3, phase 2)
- `tests/integration/` — integration tests (Dev 1, phase 3)
- `tests/e2e/` — E2E audit tests (Dev 1, phase 3)

## 3. Workflow Optimizations

- Always use `rg` (ripgrep) for content searching, never `grep`.
- Use `rtk` prefix for terminal commands (e.g. `rtk git status`).
- Use `simple-caveman` mode for concise responses.
- Follow `karpathy-guidelines`: surgical changes, avoid overcomplication, define verifiable success criteria.

## 4. References

| Topic | File |
|---|---|
| CLI commands & daemon spec | [`docs/requirements.md`](docs/requirements.md) |
| QA verification checklist | [`docs/audit.md`](docs/audit.md) |
| Test plan, file mapping, audit→test mapping | [`development_plan.md`](development_plan.md) |
| Project overview, CLI usage, architecture | [`README.md`](README.md) |
| Developer roles, phases, deliverables | [`development_plan.md`](development_plan.md) |

## 5. Quick Commands

```bash
# Run tests
python3 -m unittest discover -s tests -v               # all
python3 -m unittest discover -s tests/unit -v           # unit (phase 2 gate)
python3 -m unittest discover -s tests/integration -v    # integration
python3 -m unittest discover -s tests/e2e -v            # E2E audit
```
