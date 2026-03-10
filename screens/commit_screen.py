from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Button, Input, Label, Static
from textual.containers import Vertical, Horizontal
from typing import Optional


class CommitScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="commit-dialog"):
            yield Label("New Commit", classes="form-title")
            yield Label("Message", classes="form-label")
            yield Input(id="message", placeholder="Commit message…")
            yield Static("", id="error", classes="error-msg")
            with Horizontal():
                yield Button("Commit", variant="primary", id="commit-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
            return
        self._do_commit()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._do_commit()

    def _do_commit(self) -> None:
        msg = self.query_one("#message", Input).value.strip()
        if not msg:
            self.query_one("#error", Static).update("[red]Message cannot be empty.[/red]")
            return
        self.dismiss(msg)
