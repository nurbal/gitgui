from textual.widgets import DataTable
from typing import List
from core.repo_manager import Commit


class CommitLog(DataTable):
    def on_mount(self) -> None:
        self.add_columns("Hash", "Message", "Author", "Date")
        self.cursor_type = "row"
        self.border_title = "Commit Log"
        self.zebra_stripes = True

    def load_commits(self, commits: List[Commit]) -> None:
        self.clear()
        for c in commits:
            msg = c.message[:58] + "…" if len(c.message) > 58 else c.message
            self.add_row(c.short_hash, msg, c.author, c.date, key=c.hash)
