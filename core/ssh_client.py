import paramiko
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class SSHConfig:
    host: str
    port: int = 22
    username: str = ""
    password: Optional[str] = None
    key_path: Optional[str] = None


class SSHClient:
    def __init__(self, config: SSHConfig) -> None:
        self.config = config
        self._client: Optional[paramiko.SSHClient] = None

    def connect(self) -> None:
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs: dict = {
            "hostname": self.config.host,
            "port": self.config.port,
            "username": self.config.username,
        }
        if self.config.key_path:
            kwargs["key_filename"] = self.config.key_path
        elif self.config.password:
            kwargs["password"] = self.config.password
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

    def is_connected(self) -> bool:
        return self._client is not None
