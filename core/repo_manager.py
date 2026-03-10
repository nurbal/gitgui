from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FileStatus:
    path: str
    staged: bool
    status: str  # 'M', 'A', 'D', '?', 'R', etc.


@dataclass
class Commit:
    hash: str
    short_hash: str
    message: str
    author: str
    date: str


@dataclass
class Branch:
    name: str
    is_current: bool
    is_remote: bool


class RepoManager(ABC):

    @abstractmethod
    def get_status(self) -> List[FileStatus]: ...

    @abstractmethod
    def get_log(self, max_count: int = 50) -> List[Commit]: ...

    @abstractmethod
    def get_graph_log(self, max_count: int = 200) -> str: ...

    @abstractmethod
    def get_diff(self, file_path: Optional[str] = None, staged: bool = False) -> str: ...

    @abstractmethod
    def get_commit_diff(self, commit_hash: str) -> str: ...

    @abstractmethod
    def get_branches(self) -> List[str]: ...

    @abstractmethod
    def get_all_branches(self) -> List[Branch]: ...

    @abstractmethod
    def get_current_branch(self) -> str: ...

    @abstractmethod
    def stage(self, path: str) -> None: ...

    @abstractmethod
    def unstage(self, path: str) -> None: ...

    @abstractmethod
    def commit(self, message: str) -> None: ...

    @abstractmethod
    def checkout(self, branch: str) -> None: ...

    @abstractmethod
    def checkout_detached(self, ref: str) -> None: ...

    @abstractmethod
    def create_branch(self, name: str) -> None: ...

    @abstractmethod
    def delete_branch(self, name: str, force: bool = False) -> None: ...

    @abstractmethod
    def merge(self, branch: str) -> str: ...

    @abstractmethod
    def rebase(self, onto: str) -> str: ...

    @abstractmethod
    def pull(self) -> str: ...

    @abstractmethod
    def push(self) -> str: ...
