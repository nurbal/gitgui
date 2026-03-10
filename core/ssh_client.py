import subprocess


def test_connection(host: str) -> None:
    """Verify SSH connectivity to host. Raises RuntimeError on failure."""
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host, "echo ok"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        msg = result.stderr.strip() or "Connection failed"
        raise RuntimeError(msg)
