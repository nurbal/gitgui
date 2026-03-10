from textual.widgets import Tree
from textual.message import Message
from typing import List
from core.repo_manager import FileStatus


STATUS_ICONS = {'M': '●', 'A': '+', 'D': '✕', '?': '?', 'R': '→', 'U': '!'}
STATUS_STYLES = {'M': 'yellow', 'A': 'green', 'D': 'red', '?': 'dim', 'R': 'blue', 'U': 'bright_red'}


class FileStatusTree(Tree):
    BINDINGS = [
        ("s", "stage", "Stage"),
        ("u", "unstage", "Unstage"),
    ]

    class FileSelected(Message):
        def __init__(self, file_status: FileStatus) -> None:
            super().__init__()
            self.file_status = file_status

    class StageRequested(Message):
        def __init__(self, file_status: FileStatus) -> None:
            super().__init__()
            self.file_status = file_status

    class UnstageRequested(Message):
        def __init__(self, file_status: FileStatus) -> None:
            super().__init__()
            self.file_status = file_status

    def __init__(self, **kwargs) -> None:
        super().__init__("Changes", **kwargs)

    def on_mount(self) -> None:
        self.root.expand()
        self.border_title = "Changes  [dim](s=stage  u=unstage)[/dim]"

    def load_status(self, files: List[FileStatus]) -> None:
        self.clear()

        staged = [f for f in files if f.staged]
        unstaged = [f for f in files if not f.staged]

        staged_node = self.root.add(f"[green]Staged ({len(staged)})[/green]", expand=True)
        for f in staged:
            icon = STATUS_ICONS.get(f.status, f.status)
            style = STATUS_STYLES.get(f.status, 'white')
            staged_node.add_leaf(f"[{style}]{icon}[/{style}] {f.path}", data={"file": f})
        if not staged:
            staged_node.add_leaf("[dim](nothing staged)[/dim]")

        unstaged_node = self.root.add(f"[yellow]Unstaged ({len(unstaged)})[/yellow]", expand=True)
        for f in unstaged:
            icon = STATUS_ICONS.get(f.status, f.status)
            style = STATUS_STYLES.get(f.status, 'white')
            unstaged_node.add_leaf(f"[{style}]{icon}[/{style}] {f.path}", data={"file": f})
        if not unstaged:
            unstaged_node.add_leaf("[dim](working tree clean)[/dim]")

        self.root.expand()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        event.stop()
        if event.node.data and "file" in event.node.data:
            self.post_message(self.FileSelected(event.node.data["file"]))

    def action_stage(self) -> None:
        node = self.cursor_node
        if node and node.data and "file" in node.data:
            f: FileStatus = node.data["file"]
            if not f.staged:
                self.post_message(self.StageRequested(f))

    def action_unstage(self) -> None:
        node = self.cursor_node
        if node and node.data and "file" in node.data:
            f: FileStatus = node.data["file"]
            if f.staged:
                self.post_message(self.UnstageRequested(f))
