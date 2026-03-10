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

---

## 2026-03-10 — Fix remote git commands (tilde + shell quoting)

**Problem:** Two bugs in `RemoteRepo._git()` caused a refresh error on SSH repos.

1. **Tilde not expanded** — `git -C '~/SARC'` passes the literal string `~/SARC`
   to git; single-quoting prevents shell tilde expansion.
   **Fix:** replace `~` with `$HOME` and use double quotes: `git -C "$HOME/SARC"`.

2. **Pipes in format string** — `git log --pretty=format:%H|%h|%s|%an|%ci`
   has `|` chars that the remote shell interprets as pipes, splitting the command.
   **Fix:** use `shlex.quote()` on every argument passed to `_git()`, so special
   characters are safely escaped. Also removed all manual quoting scattered across methods.

**Tested** against `vm-lab:~/SARC` — branch, status and commit log all work correctly.

---

## 2026-03-10 — Branch manager dialog

New `screens/branch_screen.py` — opens with `Ctrl+B`.

### Features
| Action | How |
|---|---|
| List branches | All local + remote branches shown on open |
| Checkout | Select branch → **Checkout** button (or `c`) |
| Create & checkout | Type name in input → **Create & checkout** |
| Merge into current | Select branch → **Merge into current** |
| Rebase onto | Select branch → **Rebase onto** |
| Delete | Select local branch → **Delete** (guards against current/remote) |

- Merge and rebase show output in the status line and keep the dialog open.
- Checkout, create, and delete refresh the branch list in-place.
- On close, the main view refreshes if anything changed, and the header subtitle updates to the new current branch.

### New API on RepoManager / LocalRepo / RemoteRepo
`get_all_branches()`, `create_branch()`, `delete_branch()`, `merge()`, `rebase()`

---

## 2026-03-10 — Replace commit log with interactive history tree

### What changed
`CommitLog` (DataTable) replaced by `CommitGraph` (`widgets/commit_graph.py`), a `ListView`-based widget that renders `git log --graph --all` output as a colored ASCII tree.

### How it works
- Git is called with `--pretty=format:%x00%H%x00%h%x00%s%x00%an%x00%cd` — null bytes (`%x00`) act as field separators that never appear in graph characters.
- Each output line is classified: lines containing `\x00` are commit lines; others are pure graph connectors.
- Graph characters are colored with a cycling palette (cyan → magenta → green → yellow → blue for branch lanes).
- Commit lines show: `<colored graph> <hash> <message> <author> <date>`
- Navigation: arrow keys scroll the tree. **Enter or click** on a commit line loads its diff in the diff panel. Pure connector lines are navigable but produce no action (avoids SSH round-trips on every keypress).
- `get_graph_log()` added to `RepoManager`, `LocalRepo`, and `RemoteRepo`.

---

## 2026-03-10 — Branch labels and tags in history tree

Added `%D` (decoration) as a 6th null-separated field in the git log format.
Decorations are colored inline, just before the short hash on each commit line:

| Ref type | Color |
|---|---|
| `HEAD -> branch` | bold red + bold green |
| `tag: v1.0` | bold yellow |
| `origin/branch` | cyan |
| local branch | green |

---

## 2026-03-10 — Auto-scroll history tree to HEAD on load

Added `is_head: bool` to `_GraphEntry`, set when the decoration contains `HEAD ->`.
After `load_graph()` populates the `ListView`, `call_after_refresh` sets `ListView.index` to the HEAD entry so the view is centered on the current commit.

---

## 2026-03-10 — Checkout from history tree

Press `c` on any commit in the history tree:

| Refs on commit | Behaviour |
|---|---|
| None | Checkout by hash (detached HEAD) |
| 1 ref | Checkout directly |
| 2+ refs | `CheckoutPickerScreen` — scrollable list of refs, **Enter** or **Checkout selected**, plus a **Detached HEAD** fallback |

`_parse_refs()` normalises decoration strings: strips bare `HEAD` and `*/HEAD` aliases, unwraps `HEAD -> branch` and `tag: x` into plain names.
After checkout the tree refreshes and the header subtitle updates to the new branch.

---

## 2026-03-10 — Fix checkout always giving detached HEAD

**Root cause:** `git checkout origin/foo` puts git in detached HEAD mode.

**Fix:** switched to `git switch` (available since git 2.23, vm-lab has 2.25.1):
- `checkout(branch)` → `git switch branch` — DWIM mode auto-creates a local tracking branch when given a remote ref like `origin/foo`
- New `checkout_detached(ref)` → `git switch --detach ref`
- `_do_checkout()` in `app.py` detects raw commit hashes (4–40 hex chars) and routes them to `checkout_detached` with a "Detached HEAD" warning; all named refs use `checkout()`
