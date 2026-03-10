from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree
from textual.containers import Horizontal, Vertical
from typing import Optional

from core.repo_manager import RepoManager
from widgets.commit_graph import CommitGraph
from widgets.file_status import FileStatusTree
from widgets.diff_view import DiffView
from screens.repo_picker import RepoPickerScreen
from screens.ssh_screen import SSHScreen
from screens.commit_screen import CommitScreen
from screens.branch_screen import BranchScreen
from screens.checkout_picker import CheckoutPickerScreen


class GitGuiApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "GitGUI"

    BINDINGS = [
        ("ctrl+o", "open_local", "Open local"),
        ("ctrl+e", "open_ssh", "SSH connect"),
        ("ctrl+r", "refresh", "Refresh"),
        ("ctrl+b", "branches", "Branches"),
        ("ctrl+k", "commit", "Commit"),
        ("ctrl+p", "push", "Push"),
        ("ctrl+l", "pull", "Pull"),
        ("f5", "refresh", "Refresh"),
        ("ctrl+q", "quit", "Quit"),
    ]

    _repo: Optional[RepoManager] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-layout"):
            yield FileStatusTree(id="file-status")
            with Vertical(id="right-panel"):
                yield CommitGraph(id="commit-graph")
                yield DiffView(id="diff-view")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = "No repository open — Ctrl+O local  |  Ctrl+E SSH"

    # ── Repo loading ──────────────────────────────────────────────────────────

    def load_repo(self, repo: RepoManager, label: str = "") -> None:
        self._repo = repo
        branch = repo.get_current_branch()
        self.sub_title = f" {branch}   {label}"
        self._refresh_all()

    def _refresh_all(self) -> None:
        if not self._repo:
            return
        try:
            self.query_one(FileStatusTree).load_status(self._repo.get_status())
            self.query_one(CommitGraph).load_graph(self._repo.get_graph_log())
            self.query_one(DiffView).show_diff("")
        except Exception as e:
            self.notify(f"Refresh error: {e}", severity="error")

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_open_local(self) -> None:
        self.push_screen(RepoPickerScreen(), callback=self._on_repo_result)

    def action_open_ssh(self) -> None:
        self.push_screen(SSHScreen(), callback=self._on_repo_result)

    def action_refresh(self) -> None:
        if not self._repo:
            self.notify("No repository open.", severity="warning")
            return
        self._refresh_all()
        self.notify("Refreshed.", timeout=2)

    def action_branches(self) -> None:
        if not self._repo:
            self.notify("No repository open.", severity="warning")
            return
        self.push_screen(BranchScreen(self._repo), callback=self._on_branch_result)

    def _on_branch_result(self, changed: bool) -> None:
        if changed:
            self._refresh_all()
            branch = self._repo.get_current_branch()
            # Update subtitle with new branch name
            parts = self.sub_title.split("  ", 1)
            label = parts[1] if len(parts) > 1 else ""
            self.sub_title = f" {branch}   {label}"

    def action_commit(self) -> None:
        if not self._repo:
            self.notify("No repository open.", severity="warning")
            return
        self.push_screen(CommitScreen(), callback=self._on_commit_result)

    def action_push(self) -> None:
        if not self._repo:
            self.notify("No repository open.", severity="warning")
            return
        try:
            result = self._repo.push()
            self.notify(f"Pushed: {result or 'OK'}")
        except Exception as e:
            self.notify(f"Push failed: {e}", severity="error")

    def action_pull(self) -> None:
        if not self._repo:
            self.notify("No repository open.", severity="warning")
            return
        try:
            result = self._repo.pull()
            self.notify(f"Pulled: {result or 'OK'}")
            self._refresh_all()
        except Exception as e:
            self.notify(f"Pull failed: {e}", severity="error")

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_repo_result(self, result) -> None:
        if result:
            repo, label = result
            self.load_repo(repo, label)

    def _on_commit_result(self, message: Optional[str]) -> None:
        if not message or not self._repo:
            return
        try:
            self._repo.commit(message)
            self.notify("Committed successfully!")
            self._refresh_all()
        except Exception as e:
            self.notify(f"Commit failed: {e}", severity="error")

    # ── Widget event handlers ─────────────────────────────────────────────────

    def on_file_status_tree_file_selected(self, event: FileStatusTree.FileSelected) -> None:
        if not self._repo:
            return
        diff = self._repo.get_diff(event.file_status.path, staged=event.file_status.staged)
        self.query_one(DiffView).show_diff(diff)

    def on_file_status_tree_stage_requested(self, event: FileStatusTree.StageRequested) -> None:
        if not self._repo:
            return
        try:
            self._repo.stage(event.file_status.path)
            self.notify(f"Staged: {event.file_status.path}", timeout=2)
            self._refresh_all()
        except Exception as e:
            self.notify(f"Stage failed: {e}", severity="error")

    def on_file_status_tree_unstage_requested(self, event: FileStatusTree.UnstageRequested) -> None:
        if not self._repo:
            return
        try:
            self._repo.unstage(event.file_status.path)
            self.notify(f"Unstaged: {event.file_status.path}", timeout=2)
            self._refresh_all()
        except Exception as e:
            self.notify(f"Unstage failed: {e}", severity="error")

    def on_commit_graph_commit_selected(self, event: CommitGraph.CommitSelected) -> None:
        if not self._repo:
            return
        diff = self._repo.get_commit_diff(event.commit_hash)
        self.query_one(DiffView).show_diff(diff)

    def on_commit_graph_checkout_requested(self, event: CommitGraph.CheckoutRequested) -> None:
        if not self._repo:
            return
        refs = event.refs
        if len(refs) == 0:
            # No named refs → detached HEAD checkout
            self._do_checkout(event.commit_hash)
        elif len(refs) == 1:
            self._do_checkout(refs[0])
        else:
            self.push_screen(
                CheckoutPickerScreen(event.commit_hash, refs),
                callback=self._on_checkout_picked,
            )

    def _on_checkout_picked(self, target: Optional[str]) -> None:
        if target:
            self._do_checkout(target)

    def _do_checkout(self, target: str) -> None:
        try:
            self._repo.checkout(target)
            self.notify(f"Checked out: {target}")
            self._refresh_all()
            branch = self._repo.get_current_branch()
            parts = self.sub_title.split("  ", 1)
            label = parts[1] if len(parts) > 1 else ""
            self.sub_title = f" {branch}   {label}"
        except Exception as e:
            self.notify(f"Checkout failed: {e}", severity="error")
