import os
import paramiko
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


@dataclass
class SSHConfig:
    host: str                        # hostname or ~/.ssh/config alias
    port: Optional[int] = None       # override; None = use config file
    username: Optional[str] = None   # override; None = use config file
    password: Optional[str] = None
    key_path: Optional[str] = None   # override; None = use config file


class SSHClient:
    def __init__(self, config: SSHConfig) -> None:
        self.config = config
        self._client: Optional[paramiko.SSHClient] = None
        self._jump_client: Optional[paramiko.SSHClient] = None

    # ── SSH config resolution ──────────────────────────────────────────────

    @staticmethod
    def _load_ssh_config() -> paramiko.SSHConfig:
        cfg = paramiko.SSHConfig()
        config_path = Path.home() / ".ssh" / "config"
        if config_path.exists():
            with open(config_path) as f:
                cfg.parse(f)
        return cfg

    def _resolve(self) -> dict:
        """Merge ~/.ssh/config with any explicit overrides in SSHConfig."""
        file_cfg = self._load_ssh_config().lookup(self.config.host)

        hostname = file_cfg.get("hostname", self.config.host)
        port = self.config.port or int(file_cfg.get("port", 22))
        username = self.config.username or file_cfg.get("user") or os.getlogin()

        key_files = None
        if self.config.key_path:
            key_files = [self.config.key_path]
        elif "identityfile" in file_cfg:
            key_files = [os.path.expanduser(k) for k in file_cfg["identityfile"]]

        # ProxyJump may be a comma-separated chain; we only handle single hop
        proxyjump = file_cfg.get("proxyjump")
        if proxyjump:
            proxyjump = proxyjump.split(",")[0].strip()

        return {
            "hostname": hostname,
            "port": port,
            "username": username,
            "key_files": key_files,
            "proxyjump": proxyjump,
        }

    # ── ProxyJump support ─────────────────────────────────────────────────

    def _open_proxy_channel(self, proxyjump: str, target_host: str, target_port: int):
        """Connect through a jump host and return an open channel to the target."""
        # Parse "user@host:port" — each part is optional
        proxy_user, proxy_host, proxy_port_override = None, proxyjump, None
        if "@" in proxyjump:
            proxy_user, proxy_host = proxyjump.rsplit("@", 1)
        if ":" in proxy_host:
            proxy_host, p = proxy_host.rsplit(":", 1)
            proxy_port_override = int(p)

        # Resolve jump host through SSH config as well
        jump_cfg = self._load_ssh_config().lookup(proxy_host)
        jump_hostname = jump_cfg.get("hostname", proxy_host)
        jump_port = proxy_port_override or int(jump_cfg.get("port", 22))
        jump_user = proxy_user or jump_cfg.get("user") or os.getlogin()
        jump_keys = [os.path.expanduser(k) for k in jump_cfg.get("identityfile", [])]

        self._jump_client = paramiko.SSHClient()
        self._jump_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs: dict = {"hostname": jump_hostname, "port": jump_port, "username": jump_user}
        if jump_keys:
            kwargs["key_filename"] = jump_keys
        self._jump_client.connect(**kwargs)

        return self._jump_client.get_transport().open_channel(
            "direct-tcpip", (target_host, target_port), ("", 0)
        )

    # ── Public API ────────────────────────────────────────────────────────

    def connect(self) -> None:
        cfg = self._resolve()

        sock = None
        if cfg["proxyjump"]:
            sock = self._open_proxy_channel(cfg["proxyjump"], cfg["hostname"], cfg["port"])

        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        kwargs: dict = {
            "hostname": cfg["hostname"],
            "port": cfg["port"],
            "username": cfg["username"],
        }
        if self.config.password:
            kwargs["password"] = self.config.password
        if cfg["key_files"]:
            kwargs["key_filename"] = cfg["key_files"]
        if sock:
            kwargs["sock"] = sock

        self._client.connect(**kwargs)

    def run(self, command: str) -> Tuple[str, str]:
        if not self._client:
            raise RuntimeError("Not connected")
        _, stdout, stderr = self._client.exec_command(command)
        return stdout.read().decode(), stderr.read().decode()

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
        if self._jump_client:
            self._jump_client.close()
            self._jump_client = None

    def is_connected(self) -> bool:
        return self._client is not None
