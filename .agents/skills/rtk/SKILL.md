---
name: rtk
description: Use RTK (Rust Token Killer) to compress terminal command outputs and optimize token consumption.
---

Always prefix shell commands with `rtk` to minimize token consumption when executing terminal commands in this workspace.

## Usage

When running terminal commands, prefix them with `rtk`:

```bash
rtk git status
rtk git diff
rtk ls <dir>
rtk grep "<pattern>" <path>
rtk find "<pattern>" <path>
```

## Meta Commands

- `rtk gain`: Show token savings.
- `rtk gain --history`: Command history with savings.
- `rtk discover`: Find missed RTK opportunities.
- `rtk proxy <cmd>`: Run raw command without filtering.
