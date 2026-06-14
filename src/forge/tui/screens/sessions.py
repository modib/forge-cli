from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import DataTable, Label, RichLog, Button
from textual.containers import Vertical, Horizontal
from ..models import WorkspaceData, SessionRow


class SessionDetail(ModalScreen):
    def __init__(self, session: SessionRow, transcript: str = ""):
        super().__init__()
        self.session = session
        self.transcript = transcript

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"[bold]Session: {self.session.session_id}[/]", classes="section-header")
            yield RichLog(id="session-detail-content", highlight=True, markup=True)
            with Horizontal():
                yield Button("Close", variant="primary", id="close-detail")

    def on_mount(self):
        log = self.query_one("#session-detail-content", RichLog)
        s = self.session
        log.write(f"Agent:   {s.agent}")
        log.write(f"Started: {s.started}")
        if s.feature:
            log.write(f"Feature: {s.feature}")
        if s.context:
            log.write(f"Context: {s.context}")
        log.write(f"Elapsed: {s.elapsed}")
        if self.transcript:
            lines = self.transcript.split("\n")
            log.write("")
            log.write(f"[bold]Transcript ({len(lines)} lines):[/]")
            for line in lines[:50]:
                log.write(f"  {line}")
            if len(lines) > 50:
                log.write(f"  [dim]... ({len(lines) - 50} more lines)[/]")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "close-detail":
            self.app.pop_screen()


class SessionsScreen(Widget):
    def compose(self) -> ComposeResult:
        yield Label("Sessions", classes="section-header")
        yield DataTable(id="session-table", cursor_type="row")

    def on_mount(self):
        table = self.query_one("#session-table", DataTable)
        table.add_columns("ID", "Agent", "Feature", "Started", "Context")

    def refresh_data(self, data: WorkspaceData):
        table = self.query_one("#session-table", DataTable)
        table.clear()
        self._sessions = data.sessions
        for s in data.sessions:
            feat = f"({s.feature})" if s.feature else ""
            ctx = s.context[:40] + "..." if len(s.context) > 40 else s.context
            table.add_row(s.session_id[:16], s.agent, feat, s.started, ctx)

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        if hasattr(self, "_sessions") and event.cursor_row is not None:
            if 0 <= event.cursor_row < len(self._sessions):
                s = self._sessions[event.cursor_row]
                import os
                from ... import config as cfg
                transcript = ""
                tpath = os.path.join(cfg.WORKSPACE_DIR, "sessions", s.session_id, "transcript.md")
                if os.path.exists(tpath):
                    with open(tpath) as f:
                        transcript = f.read()
                self.app.push_screen(SessionDetail(s, transcript))
