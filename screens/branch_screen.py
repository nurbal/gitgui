from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Button, Input, Label, ListItem, ListView, Static
from textual.containers import Vertical, Horizontal
from core.repo_manager import RepoManager, Branch
from typing import List, Optional


class BranchScreen(ModalScreen):
    BINDINGS = [
        ("escape", "dismiss_screen", "Close"),
        ("c", "focus_checkout", "Checkout"),
        ("n", "focus_new", "New branch"),
        ("d", "focus_delete", "Delete"),
    ]

    def __init__(self, repo: RepoManager) -> None:
        super().__init__()
        self._repo = repo
        self._branches: List[Branch] = []
        self._changed = False

    def compose(self) -> ComposeResult:
        with Vertical(id="branch-dialog"):
            yield Label("Branch Manager", classes="form-title")

            yield ListView(id="branch-list")

            with Horizontal(id="create-row"):
                yield Input(placeholder="new-branch-name", id="new-branch-input")
                yield Button("Create & checkout", id="create-btn", variant="success")

            with Horizontal(id="action-row"):
                yield Button("Checkout", id="checkout-btn", variant="primary")
                yield Button("Merge into current", id="merge-btn")
                yield Button("Rebase onto", id="rebase-btn")
                yield Button("Delete", id="delete-btn", variant="error")
                yield Button("Close", id="close-btn")

            yield Static("", id="branch-status")

    def on_mount(self) -> None:
        self._load_branches()

    # ── Branch list ───────────────────────────────────────────────────────────

    def _load_branches(self) -> None:
        lv = self.query_one("#branch-list", ListView)
        lv.clear()
        try:
            self._branches = self._repo.get_all_branches()
            for b in self._branches:
                if b.is_current:
                    text = f"[bold green]● {b.name}[/bold green]  [dim](current)[/dim]"
                elif b.is_remote:
                    text = f"[dim]  {b.name}[/dim]"
                else:
                    text = f"  {b.name}"
                lv.append(ListItem(Label(text)))
        except Exception as e:
            self._status(f"[red]Could not load branches: {e}[/red]")

    def _highlighted_branch(self) -> Optional[Branch]:
        lv = self.query_one("#branch-list", ListView)
        idx = lv.index
        if idx is not None and 0 <= idx < len(self._branches):
            return self._branches[idx]
        return None

    # ── Status line ───────────────────────────────────────────────────────────

    def _status(self, msg: str) -> None:
        self.query_one("#branch-status", Static).update(msg)

    # ── Button handler ────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        handlers = {
            "close-btn":    self._do_close,
            "create-btn":   self._do_create,
            "checkout-btn": self._do_checkout,
            "merge-btn":    self._do_merge,
            "rebase-btn":   self._do_rebase,
            "delete-btn":   self._do_delete,
        }
        handler = handlers.get(event.button.id or "")
        if handler:
            handler()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _do_close(self) -> None:
        self.dismiss(self._changed)

    def _do_create(self) -> None:
        name = self.query_one("#new-branch-input", Input).value.strip()
        if not name:
            self._status("[red]Branch name is required.[/red]")
            return
        try:
            self._repo.create_branch(name)
            self._repo.checkout(name)
            self._status(f"[green]Created and checked out '{name}'.[/green]")
            self.query_one("#new-branch-input", Input).value = ""
            self._changed = True
            self._load_branches()
        except Exception as e:
            self._status(f"[red]{e}[/red]")

    def _do_checkout(self) -> None:
        b = self._highlighted_branch()
        if not b:
            self._status("[red]Select a branch first.[/red]")
            return
        if b.is_current:
            self._status(f"[yellow]Already on '{b.name}'.[/yellow]")
            return
        try:
            self._repo.checkout(b.name)
            self._status(f"[green]Checked out '{b.name}'.[/green]")
            self._changed = True
            self._load_branches()
        except Exception as e:
            self._status(f"[red]{e}[/red]")

    def _do_merge(self) -> None:
        b = self._highlighted_branch()
        if not b:
            self._status("[red]Select a branch to merge.[/red]")
            return
        try:
            result = self._repo.merge(b.name)
            self._status(f"[green]Merged '{b.name}': {result or 'OK'}[/green]")
            self._changed = True
        except Exception as e:
            self._status(f"[red]Merge failed: {e}[/red]")

    def _do_rebase(self) -> None:
        b = self._highlighted_branch()
        if not b:
            self._status("[red]Select a branch to rebase onto.[/red]")
            return
        try:
            result = self._repo.rebase(b.name)
            self._status(f"[green]Rebased onto '{b.name}': {result or 'OK'}[/green]")
            self._changed = True
        except Exception as e:
            self._status(f"[red]Rebase failed: {e}[/red]")

    def _do_delete(self) -> None:
        b = self._highlighted_branch()
        if not b:
            self._status("[red]Select a branch to delete.[/red]")
            return
        if b.is_current:
            self._status("[red]Cannot delete the currently checked-out branch.[/red]")
            return
        if b.is_remote:
            self._status("[red]Remote branch deletion not supported here.[/red]")
            return
        try:
            self._repo.delete_branch(b.name)
            self._status(f"[green]Deleted '{b.name}'.[/green]")
            self._changed = True
            self._load_branches()
        except Exception as e:
            # Offer force-delete hint if it's an unmerged branch error
            self._status(f"[red]{e}[/red]  [dim](branch may be unmerged)[/dim]")

    # ── Key action helpers ────────────────────────────────────────────────────

    def action_dismiss_screen(self) -> None:
        self.dismiss(self._changed)

    def action_focus_checkout(self) -> None:
        self.query_one("#checkout-btn", Button).focus()

    def action_focus_new(self) -> None:
        self.query_one("#new-branch-input", Input).focus()

    def action_focus_delete(self) -> None:
        self.query_one("#delete-btn", Button).focus()
