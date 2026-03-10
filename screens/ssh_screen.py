from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Button, Collapsible, Input, Label, Static
from textual.containers import Vertical, Horizontal
from core.ssh_client import SSHClient, SSHConfig
from core.remote_repo import RemoteRepo


class SSHScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="ssh-form"):
            yield Label("SSH Connection", classes="form-title")

            yield Label("Host  [dim](hostname or ~/.ssh/config alias)[/dim]", classes="form-label")
            yield Input(placeholder="vm-lab", id="host")

            yield Label("Remote repository path", classes="form-label")
            yield Input(placeholder="/home/user/myrepo", id="repo-path")

            with Collapsible(title="Advanced  (overrides ~/.ssh/config)", collapsed=True):
                yield Label("Port", classes="form-label")
                yield Input(placeholder="22", id="port")
                yield Label("Username", classes="form-label")
                yield Input(placeholder="", id="username")
                yield Label("Password", classes="form-label")
                yield Input(placeholder="", id="password", password=True)
                yield Label("SSH key path", classes="form-label")
                yield Input(placeholder="~/.ssh/id_rsa", id="key-path")

            yield Static("", id="error", classes="error-msg")

            with Horizontal():
                yield Button("Connect", variant="primary", id="connect-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "connect-btn":
            self._do_connect()

    def _do_connect(self) -> None:
        host = self.query_one("#host", Input).value.strip()
        repo_path = self.query_one("#repo-path", Input).value.strip()

        if not host or not repo_path:
            self.query_one("#error", Static).update(
                "[red]Host and repository path are required.[/red]"
            )
            return

        port_str = self.query_one("#port", Input).value.strip()
        username = self.query_one("#username", Input).value.strip() or None
        password = self.query_one("#password", Input).value or None
        key_path = self.query_one("#key-path", Input).value.strip() or None

        port = None
        if port_str:
            try:
                port = int(port_str)
            except ValueError:
                self.query_one("#error", Static).update("[red]Port must be a number.[/red]")
                return

        config = SSHConfig(host=host, port=port, username=username,
                           password=password, key_path=key_path)
        try:
            self.query_one("#error", Static).update("[yellow]Connecting…[/yellow]")
            client = SSHClient(config)
            client.connect()
            repo = RemoteRepo(client, repo_path)
            label = f"{host}:{repo_path}"
            self.dismiss((repo, label))
        except Exception as e:
            self.query_one("#error", Static).update(f"[red]Connection failed: {e}[/red]")
