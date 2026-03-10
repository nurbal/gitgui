from dataclasses import dataclass
from typing import List, Optional

from rich.text import Text
from textual.message import Message
from textual.widgets import Label, ListItem, ListView


# ── Graph line coloring ───────────────────────────────────────────────────────

# Cycle through these styles for different branch "lanes"
_LANE_STYLES = ["bright_cyan", "bright_magenta", "bright_green", "bright_yellow", "bright_blue"]


def _color_graph(prefix: str) -> Text:
    """Colorize git --graph ASCII art characters."""
    t = Text()
    lane = 0
    for ch in prefix:
        if ch == '*':
            t.append(ch, style=f"bold {_LANE_STYLES[lane % len(_LANE_STYLES)]}")
        elif ch in '|':
            t.append(ch, style=_LANE_STYLES[lane % len(_LANE_STYLES)])
            lane += 1
        elif ch in '/\\':
            t.append(ch, style="dim bright_blue")
        elif ch == '-':
            t.append(ch, style="dim")
        elif ch == '_':
            t.append(ch, style="dim")
        else:
            t.append(ch)
    return t


# ── Entry dataclass ───────────────────────────────────────────────────────────

@dataclass
class _GraphEntry:
    display: Text
    commit_hash: Optional[str]  # None for pure graph lines


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_graph_output(raw: str) -> List[_GraphEntry]:
    """
    Parse git log --graph output where commit lines contain \x00 separators.
    Format used: --pretty=format:%x00%H%x00%h%x00%s%x00%an%x00%cd
    """
    entries: List[_GraphEntry] = []

    for line in raw.splitlines():
        if '\x00' in line:
            null_idx = line.index('\x00')
            graph_prefix = line[:null_idx]
            parts = line[null_idx + 1:].split('\x00', 4)

            if len(parts) == 5:
                full_hash, short_hash, message, author, date = parts
                t = _color_graph(graph_prefix)
                t.append(f" {short_hash}", style="yellow")
                t.append("  ")
                msg = (message[:56] + "…") if len(message) > 56 else message
                t.append(msg)
                t.append(f"  {author}", style="dim green")
                t.append(f"  {date}", style="dim")
                entries.append(_GraphEntry(display=t, commit_hash=full_hash))
                continue

        # Pure graph / connector line
        t = _color_graph(line)
        entries.append(_GraphEntry(display=t, commit_hash=None))

    return entries


# ── Widget ────────────────────────────────────────────────────────────────────

class CommitGraph(ListView):
    """Scrollable, interactive git history tree."""

    class CommitSelected(Message):
        def __init__(self, commit_hash: str) -> None:
            super().__init__()
            self.commit_hash = commit_hash

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._entries: List[_GraphEntry] = []

    def on_mount(self) -> None:
        self.border_title = "History  [dim](Enter = show diff)[/dim]"

    def load_graph(self, raw: str) -> None:
        self.clear()
        self._entries = parse_graph_output(raw)
        for entry in self._entries:
            self.append(ListItem(Label(entry.display)))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Fire CommitSelected only on Enter / click — avoids SSH round-trips on every arrow key."""
        event.stop()
        idx = self.index
        if idx is not None and 0 <= idx < len(self._entries):
            entry = self._entries[idx]
            if entry.commit_hash:
                self.post_message(self.CommitSelected(entry.commit_hash))
