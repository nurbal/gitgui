import git
from typing import List, Optional
from .repo_manager import RepoManager, FileStatus, Commit


class LocalRepo(RepoManager):
    def __init__(self, path: str) -> None:
        self.path = path
        self.repo = git.Repo(path, search_parent_directories=True)

    def get_status(self) -> List[FileStatus]:
        files: List[FileStatus] = []

        # Staged changes vs HEAD
        try:
            for item in self.repo.index.diff("HEAD"):
                files.append(FileStatus(
                    path=item.a_path,
                    staged=True,
                    status=item.change_type[0],
                ))
        except git.BadName:
            # Brand-new repo with no commits yet
            for key in self.repo.index.entries:
                files.append(FileStatus(path=key[0], staged=True, status='A'))

        # Unstaged changes
        for item in self.repo.index.diff(None):
            files.append(FileStatus(
                path=item.a_path,
                staged=False,
                status=item.change_type[0],
            ))

        # Untracked files
        for path in self.repo.untracked_files:
            files.append(FileStatus(path=path, staged=False, status='?'))

        return files

    def get_log(self, max_count: int = 50) -> List[Commit]:
        commits: List[Commit] = []
        try:
            for c in self.repo.iter_commits(max_count=max_count):
                commits.append(Commit(
                    hash=c.hexsha,
                    short_hash=c.hexsha[:7],
                    message=c.message.strip().split('\n')[0],
                    author=str(c.author),
                    date=c.committed_datetime.strftime('%Y-%m-%d %H:%M'),
                ))
        except Exception:
            pass
        return commits

    def get_diff(self, file_path: Optional[str] = None, staged: bool = False) -> str:
        try:
            args = ['--cached'] if staged else []
            if file_path:
                args.append(file_path)
            return self.repo.git.diff(*args) or "(no changes)"
        except Exception as e:
            return f"Error: {e}"

    def get_commit_diff(self, commit_hash: str) -> str:
        try:
            return self.repo.git.show(commit_hash, '--patch', '--no-color')
        except Exception as e:
            return f"Error: {e}"

    def get_branches(self) -> List[str]:
        return [b.name for b in self.repo.branches]

    def get_current_branch(self) -> str:
        try:
            return self.repo.active_branch.name
        except TypeError:
            return "(detached HEAD)"

    def stage(self, path: str) -> None:
        self.repo.index.add([path])

    def unstage(self, path: str) -> None:
        self.repo.git.reset('HEAD', path)

    def commit(self, message: str) -> None:
        self.repo.index.commit(message)

    def checkout(self, branch: str) -> None:
        self.repo.git.checkout(branch)

    def pull(self) -> str:
        return self.repo.git.pull()

    def push(self) -> str:
        return self.repo.git.push()
