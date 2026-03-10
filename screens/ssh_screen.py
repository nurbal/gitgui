from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Button, Input, Label, Static
from textual.containers import Vertical, Horizontal
from core.ssh_client import test_connection
from core.remote_repo import RemoteRepo


class SSHScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="ssh-form"):
            yield Label("SSH Connection", classes="form-title")

            yield Label(
                "Host  [dim](hostname, IP, or ~/.ssh/config alias)[/dim]",
                classes="form-label",
            )
            yield Input(placeholder="vm-lab", id="host")

            yield Label("Remote repository path", classes="form-label")
            yield Input(placeholder="/home/user/myrepo", id="repo-path")

            yield Static("", id="error", classes="error-msg")

            with Horizontal():
                yield Button("Connect", variant="primary", id="connect-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "connect-btn":
            self._do_connect()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._do_connect()

    def _do_connect(self) -> None:
        host = self.query_one("#host", Input).value.strip()
        repo_path = self.query_one("#repo-path", Input).value.strip()

        if not host or not repo_path:
            self.query_one("#error", Static).update(
                "[red]Both fields are required.[/red]"
            )
            return

        self.query_one("#error", Static).update("[yellow]Connecting…[/yellow]")
        try:
            test_connection(host)
            repo = RemoteRepo(host, repo_path)
            self.dismiss((repo, f"{host}:{repo_path}"))
        except Exception as e:
            self.query_one("#error", Static).update(f"[red]{e}[/red]")
