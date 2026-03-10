from textual.widgets import RichLog
from rich.syntax import Syntax


class DiffView(RichLog):
    def on_mount(self) -> None:
        self.border_title = "Diff"
        self.highlight = True
        self.markup = True

    def show_diff(self, content: str) -> None:
        self.clear()
        if not content or content in ("(no changes)", "(no diff)", ""):
            self.write("[dim](select a file or commit to see the diff)[/dim]")
            return
        syntax = Syntax(content, "diff", theme="monokai", line_numbers=False, word_wrap=False)
        self.write(syntax)
