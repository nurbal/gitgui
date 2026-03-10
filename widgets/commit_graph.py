from dataclasses import dataclass, field
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
    is_head: bool = False
    refs: List[str] = field(default_factory=list)  # checkout-able ref names


# ── Parser ────────────────────────────────────────────────────────────────────

def _color_decorations(raw: str) -> Text:
    """
    Color git decoration refs, e.g. "HEAD -> main, origin/main, tag: v1.0"
    - HEAD -> branch  : bold red + bold green
    - tag: ...        : bold yellow
    - origin/...      : cyan
    - local branch    : green
    """
    t = Text()
    if not raw.strip():
        return t
    t.append(" (", style="dim")
    for i, ref in enumerate(raw.split(", ")):
        if i:
            t.append(", ", style="dim")
        ref = ref.strip()
        if ref.startswith("HEAD -> "):
            t.append("HEAD", style="bold red")
            t.append(" -> ", style="dim")
            t.append(ref[len("HEAD -> "):], style="bold green")
        elif ref.startswith("tag: "):
            t.append("tag: ", style="dim yellow")
            t.append(ref[5:], style="bold yellow")
        elif "/" in ref:
            t.append(ref, style="cyan")
        else:
            t.append(ref, style="green")
    t.append(")", style="dim")
    return t


def _parse_refs(decoration: str) -> List[str]:
    """
    Extract checkout-able names from a git decoration string.
    e.g. "HEAD -> main, origin/main, tag: v1.0"  →  ["main", "origin/main", "v1.0"]
    Skips bare HEAD and */HEAD aliases.
    """
    refs: List[str] = []
    if not decoration.strip():
        return refs
    for part in decoration.split(", "):
        part = part.strip()
        if part == "HEAD" or part.endswith("/HEAD"):
            continue
        if part.startswith("HEAD -> "):
            refs.append(part[len("HEAD -> "):])
        elif part.startswith("tag: "):
            refs.append(part[5:])
        else:
            refs.append(part)
    return refs


def parse_graph_output(raw: str) -> List[_GraphEntry]:
    """
    Parse git log --graph output where commit lines contain \x00 separators.
    Format used: --pretty=format:%x00%H%x00%h%x00%s%x00%an%x00%cd%x00%D
    """
    entries: List[_GraphEntry] = []

    for line in raw.splitlines():
        if '\x00' in line:
            null_idx = line.index('\x00')
            graph_prefix = line[:null_idx]
            parts = line[null_idx + 1:].split('\x00', 5)

            if len(parts) >= 5:
                full_hash  = parts[0]
                short_hash = parts[1]
                message    = parts[2]
                author     = parts[3]
                date       = parts[4]
                decoration = parts[5] if len(parts) > 5 else ""

                is_head = "HEAD ->" in decoration
                refs = _parse_refs(decoration)

                t = _color_graph(graph_prefix)
                t.append_text(_color_decorations(decoration))
                t.append(f" {short_hash}", style="yellow")
                t.append("  ")
                msg = (message[:56] + "…") if len(message) > 56 else message
                t.append(msg)
                t.append(f"  {author}", style="dim green")
                t.append(f"  {date}", style="dim")
                entries.append(_GraphEntry(display=t, commit_hash=full_hash, is_head=is_head, refs=refs))
                continue

        # Pure graph / connector line
        t = _color_graph(line)
        entries.append(_GraphEntry(display=t, commit_hash=None))

    return entries


# ── Widget ────────────────────────────────────────────────────────────────────

class CommitGraph(ListView):
    """Scrollable, interactive git history tree."""

    BINDINGS = [("c", "checkout", "Checkout")]

    class CommitSelected(Message):
        def __init__(self, commit_hash: str) -> None:
            super().__init__()
            self.commit_hash = commit_hash

    class CheckoutRequested(Message):
        def __init__(self, commit_hash: str, refs: List[str]) -> None:
            super().__init__()
            self.commit_hash = commit_hash
            self.refs = refs  # empty = detached HEAD only; 1 = direct; 2+ = needs picker

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._entries: List[_GraphEntry] = []

    def on_mount(self) -> None:
        self.border_title = "History  [dim](Enter = diff · c = checkout)[/dim]"

    def action_checkout(self) -> None:
        idx = self.index
        if idx is not None and 0 <= idx < len(self._entries):
            entry = self._entries[idx]
            if entry.commit_hash:
                self.post_message(self.CheckoutRequested(entry.commit_hash, entry.refs))

    def load_graph(self, raw: str) -> None:
        self.clear()
        self._entries = parse_graph_output(raw)
        head_idx: Optional[int] = None
        for i, entry in enumerate(self._entries):
            self.append(ListItem(Label(entry.display)))
            if entry.is_head and head_idx is None:
                head_idx = i
        if head_idx is not None:
            self.call_after_refresh(self._scroll_to_head, head_idx)

    def _scroll_to_head(self, idx: int) -> None:
        self.index = idx

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Fire CommitSelected only on Enter / click — avoids SSH round-trips on every arrow key."""
        event.stop()
        idx = self.index
        if idx is not None and 0 <= idx < len(self._entries):
            entry = self._entries[idx]
            if entry.commit_hash:
                self.post_message(self.CommitSelected(entry.commit_hash))
