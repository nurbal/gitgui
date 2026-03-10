import shlex
import subprocess
from typing import List, Optional
from .repo_manager import RepoManager, FileStatus, Commit, Branch


class RemoteRepo(RepoManager):
    def __init__(self, host: str, repo_path: str) -> None:
        self.host = host
        # Replace ~ with $HOME so the remote shell expands it correctly.
        # Single-quoting '~/foo' would prevent tilde expansion.
        self._repo_path = repo_path.replace("~", "$HOME", 1)

    def _ssh(self, cmd: str) -> str:
        result = subprocess.run(
            ["ssh", self.host, cmd],
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        if result.returncode != 0 and not out:
            raise RuntimeError(err or f"Command failed (exit {result.returncode})")
        return out

    def _git(self, *args: str) -> str:
        # shlex.quote each argument so pipes, spaces and special chars are safe.
        # Double-quote the repo path so $HOME expands but spaces are handled.
        quoted_args = " ".join(shlex.quote(a) for a in args)
        return self._ssh(f'git -C "{self._repo_path}" {quoted_args}')

    def get_status(self) -> List[FileStatus]:
        out = self._git("status", "--porcelain")
        files: List[FileStatus] = []
        for line in out.splitlines():
            if len(line) < 3:
                continue
            staged_char = line[0]
            unstaged_char = line[1]
            path = line[3:]
            if " -> " in path:
                path = path.split(" -> ")[-1]
            if staged_char not in (" ", "?"):
                files.append(FileStatus(path=path, staged=True, status=staged_char))
            if unstaged_char not in (" ", "\x00"):
                files.append(FileStatus(
                    path=path,
                    staged=False,
                    status="?" if unstaged_char == "?" else unstaged_char,
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
            args.append(file_path)
        return self._git(*args) or "(no changes)"

    def get_commit_diff(self, commit_hash: str) -> str:
        return self._git("show", commit_hash, "--patch", "--no-color") or "(no diff)"

    def get_branches(self) -> List[str]:
        out = self._git("branch", "--list")
        return [b.strip().lstrip("* ") for b in out.splitlines() if b.strip()]

    def get_all_branches(self) -> List[Branch]:
        current = self.get_current_branch()
        branches: List[Branch] = []

        for line in self._git("branch", "--list").splitlines():
            name = line.strip().lstrip("* ")
            if name:
                branches.append(Branch(name=name, is_current=(name == current), is_remote=False))

        for line in self._git("branch", "-r", "--list").splitlines():
            name = line.strip()
            if name and "->" not in name:
                branches.append(Branch(name=name, is_current=False, is_remote=True))

        return branches

    def get_current_branch(self) -> str:
        return self._git("branch", "--show-current") or "(detached HEAD)"

    def stage(self, path: str) -> None:
        self._git("add", path)

    def unstage(self, path: str) -> None:
        self._git("reset", "HEAD", path)

    def commit(self, message: str) -> None:
        self._git("commit", "-m", message)

    def checkout(self, branch: str) -> None:
        self._git("checkout", branch)

    def create_branch(self, name: str) -> None:
        self._git("branch", name)

    def delete_branch(self, name: str, force: bool = False) -> None:
        self._git("branch", "-D" if force else "-d", name)

    def merge(self, branch: str) -> str:
        return self._git("merge", branch)

    def rebase(self, onto: str) -> str:
        return self._git("rebase", onto)

    def pull(self) -> str:
        return self._git("pull")

    def push(self) -> str:
        return self._git("push")
