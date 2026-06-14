from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog
from ..models import WorkspaceData


class LogScreen(Widget):
    def compose(self) -> ComposeResult:
        yield RichLog(id="event-log", highlight=True, markup=True, max_lines=2000)

    def refresh_data(self, data: WorkspaceData):
        log = self.query_one("#event-log", RichLog)
        log.clear()
        if not data.events:
            log.write("[dim]No events recorded[/]")
            return
        for e in data.events:
            log.write(f"[dim]{e.timestamp}[/] [bold]{e.command}[/]  {e.result}")

    def append_entry(self, command: str, result: str, timestamp: str = ""):
        log = self.query_one("#event-log", RichLog)
        log.write(f"[dim]{timestamp}[/] [bold]{command}[/]  {result}")
        log.scroll_end()
