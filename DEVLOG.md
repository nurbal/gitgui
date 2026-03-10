# GitGUI — Dev Log

## 2026-03-10 — Initial scaffold

**Goal:** Build a terminal UI Git client in Python supporting local and SSH remote repositories.

### Tech stack chosen
- **TUI framework:** `textual` (built on `rich`) — interactive widgets, mouse+keyboard, CSS-like layout
- **Local Git:** `gitpython`
- **SSH / remote Git:** `paramiko` → replaced by system `ssh` binary (see below)
- **Package manager:** `uv` with `pyproject.toml`

### Project structure
```
gitgui/
├── main.py                   # Entry point
├── app.py                    # Textual App, keybindings, event routing
├── app.tcss                  # TUI layout and styles
├── core/
│   ├── repo_manager.py       # Abstract base class (RepoManager, FileStatus, Commit)
│   ├── local_repo.py         # gitpython backend
│   ├── remote_repo.py        # subprocess ssh backend
│   └── ssh_client.py         # SSH connectivity test via subprocess
├── widgets/
│   ├── commit_log.py         # DataTable showing commit history
│   ├── file_status.py        # Tree showing staged/unstaged files
│   └── diff_view.py          # RichLog showing syntax-highlighted diffs
└── screens/
    ├── repo_picker.py        # Modal: open a local repository
    ├── ssh_screen.py         # Modal: SSH connection form
    └── commit_screen.py      # Modal: commit message input
```

### Layout
3-panel TUI:
- **Left:** file status tree (staged / unstaged), with `s`/`u` to stage/unstage
- **Top right:** commit log (DataTable), click a row to show its diff
- **Bottom right:** diff viewer (syntax highlighted)

### Key bindings
| Key | Action |
|---|---|
| `Ctrl+O` | Open local repo |
| `Ctrl+E` | Connect via SSH |
| `Ctrl+K` | Commit staged changes |
| `Ctrl+P` | Push |
| `Ctrl+L` | Pull |
| `Ctrl+R` / `F5` | Refresh |
| `s` | Stage selected file |
| `u` | Unstage selected file |
| `Ctrl+Q` | Quit |

### Git
- Repo initialised, `.gitignore` set up (excludes `__pycache__`, `.venv`, `.claude/`)
- Remote: `git@github.com:nurbal/gitgui.git`
- Initial commit pushed to `main`

---

## 2026-03-10 — SSH config support & ProxyJump

**Problem:** `paramiko` failed to connect to SSH config aliases (e.g. `vm-lab`) with
`[Errno 8] nodename nor servname provided` because it doesn't fully support all
`~/.ssh/config` directives (`Include`, `Match`, complex `ProxyJump` chains, certificates…).

**Fix:** Dropped `paramiko` for command execution. All remote git operations now run via
`subprocess` + the system `ssh` binary, which reads `~/.ssh/config` natively.

### Changes
- `core/ssh_client.py` — replaced with a lightweight connectivity test:
  `ssh -o BatchMode=yes -o ConnectTimeout=10 <host> echo ok`
- `core/remote_repo.py` — all git commands run as `ssh <host> git -C <path> <cmd>`
- `screens/ssh_screen.py` — simplified to two fields only: **host alias** + **repo path**.
  All auth, routing and jump hosts are handled transparently by the system SSH client.

### Usage
In the SSH dialog, entering just `vm-lab` and `/home/user/repo` is enough.
Every setting in the matching `~/.ssh/config` block (hostname, user, port,
IdentityFile, ProxyJump…) is applied automatically.
