import os
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Button, Input, Label, Static
from textual.containers import Vertical, Horizontal
from core.local_repo import LocalRepo


class RepoPickerScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="picker-form"):
            yield Label("Open Local Repository", classes="form-title")
            yield Label("Repository path", classes="form-label")
            yield Input(placeholder="/path/to/repo", id="repo-path", value=os.getcwd())
            yield Static("", id="error", classes="error-msg")
            with Horizontal():
                yield Button("Open", variant="primary", id="open-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
            return
        path = self.query_one("#repo-path", Input).value.strip()
        try:
            repo = LocalRepo(path)
            self.dismiss((repo, path))
        except Exception as e:
            self.query_one("#error", Static).update(f"[red]{e}[/red]")

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self.query_one("#open-btn", Button).press()
