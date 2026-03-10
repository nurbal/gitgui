from typing import List, Optional

from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Button, Label, ListItem, ListView, Static
from textual.containers import Vertical, Horizontal


class CheckoutPickerScreen(ModalScreen):
    """Ask the user which ref to checkout when a commit has several branches/tags."""

    def __init__(self, commit_hash: str, refs: List[str]) -> None:
        super().__init__()
        self._hash = commit_hash
        self._refs = refs

    def compose(self) -> ComposeResult:
        with Vertical(id="checkout-picker"):
            yield Label("Checkout", classes="form-title")
            yield Label(
                f"Commit [yellow]{self._hash[:7]}[/yellow] has multiple refs — pick one:",
                classes="form-label",
            )
            yield ListView(id="ref-list")
            yield Static("", id="picker-error", classes="error-msg")
            with Horizontal():
                yield Button("Checkout selected", variant="primary", id="ok-btn")
                yield Button("Detached HEAD", id="detached-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        lv = self.query_one("#ref-list", ListView)
        for ref in self._refs:
            lv.append(ListItem(Label(ref)))
        if self._refs:
            lv.index = 0

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "detached-btn":
            self.dismiss(self._hash)
        elif event.button.id == "ok-btn":
            lv = self.query_one("#ref-list", ListView)
            idx = lv.index
            if idx is not None and 0 <= idx < len(self._refs):
                self.dismiss(self._refs[idx])
            else:
                self.query_one("#picker-error", Static).update(
                    "[red]Select a ref first.[/red]"
                )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Allow pressing Enter on a list item as a shortcut for checkout."""
        event.stop()
        lv = self.query_one("#ref-list", ListView)
        idx = lv.index
        if idx is not None and 0 <= idx < len(self._refs):
            self.dismiss(self._refs[idx])
