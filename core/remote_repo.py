from typing import List, Optional
from .repo_manager import RepoManager, FileStatus, Commit
from .ssh_client import SSHClient


class RemoteRepo(RepoManager):
    def __init__(self, ssh_client: SSHClient, repo_path: str) -> None:
        self.client = ssh_client
        self.repo_path = repo_path

    def _git(self, *args: str) -> str:
        cmd = f"git -C '{self.repo_path}' {' '.join(args)}"
        out, err = self.client.run(cmd)
        out = out.strip()
        if not out and err.strip():
            # git pushes progress info to stderr; use it as fallback output
            out = err.strip()
        return out

    def get_status(self) -> List[FileStatus]:
        out = self._git("status", "--porcelain")
        files: List[FileStatus] = []
        for line in out.splitlines():
            if len(line) < 3:
                continue
            staged_char = line[0]
            unstaged_char = line[1]
            path = line[3:]
            # Renames: "old -> new"
            if ' -> ' in path:
                path = path.split(' -> ')[-1]
            if staged_char not in (' ', '?'):
                files.append(FileStatus(path=path, staged=True, status=staged_char))
            if unstaged_char not in (' ', '\x00'):
                files.append(FileStatus(
                    path=path,
                    staged=False,
                    status='?' if unstaged_char == '?' else unstaged_char,
                ))
        return files

    def get_log(self, max_count: int = 50) -> List[Commit]:
        fmt = "%H|%h|%s|%an|%ci"
        out = self._git("log", f"--max-count={max_count}", f"--pretty=format:{fmt}")
        commits: List[Commit] = []
        for line in out.splitlines():
            parts = line.split("|", 4)
            if len(parts) == 5:
                commits.append(Commit(
                    hash=parts[0].strip(),
                    short_hash=parts[1].strip(),
                    message=parts[2].strip(),
                    author=parts[3].strip(),
                    date=parts[4].strip()[:16],
                ))
        return commits

    def get_diff(self, file_path: Optional[str] = None, staged: bool = False) -> str:
        args = ["diff"]
        if staged:
            args.append("--cached")
        if file_path:
            args.append(f"'{file_path}'")
        return self._git(*args) or "(no changes)"

    def get_commit_diff(self, commit_hash: str) -> str:
        return self._git("show", commit_hash, "--patch", "--no-color") or "(no diff)"

    def get_branches(self) -> List[str]:
        out = self._git("branch", "--list")
        return [b.strip().lstrip("* ") for b in out.splitlines() if b.strip()]

    def get_current_branch(self) -> str:
        return self._git("branch", "--show-current") or "(detached HEAD)"

    def stage(self, path: str) -> None:
        self._git("add", f"'{path}'")

    def unstage(self, path: str) -> None:
        self._git("reset", "HEAD", f"'{path}'")

    def commit(self, message: str) -> None:
        escaped = message.replace("'", "'\\''")
        self._git("commit", "-m", f"'{escaped}'")

    def checkout(self, branch: str) -> None:
        self._git("checkout", branch)

    def pull(self) -> str:
        return self._git("pull")

    def push(self) -> str:
        return self._git("push")
