from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import DataTable, Label, RichLog, Button
from textual.containers import Vertical, Horizontal
from ..models import WorkspaceData, RepoRow


class RepoDetail(ModalScreen):
    def __init__(self, repo: RepoRow, full_status: dict | None = None):
        super().__init__()
        self.repo = repo
        self.full_status = full_status

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"[bold]{self.repo.name}[/]", classes="section-header")
            yield RichLog(id="repo-detail-content", highlight=True, markup=True)
            with Horizontal():
                yield Button("Close", variant="primary", id="close-detail")

    def on_mount(self):
        log = self.query_one("#repo-detail-content", RichLog)
        r = self.repo
        log.write(f"Path:    {r.path}")
        log.write(f"Branch:  {r.branch}")
        status = "✓" if not r.dirty else "[yellow]dirty[/]"
        log.write(f"Status:  {status}")
        log.write(f"Ahead:   {r.ahead}")
        log.write(f"Behind:  {r.behind}")
        if r.last_commit_time:
            log.write(f"Last commit:  {r.last_commit_time}")
        if r.last_commit_msg:
            log.write(f"  [dim]{r.last_commit_msg}[/]")
        if r.remote_url:
            log.write(f"Remote:  {r.remote_url}")
        if self.full_status:
            log.write("")
            log.write("[bold]Full status:[/]")
            log.write(str(self.full_status))

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "close-detail":
            self.app.pop_screen()


class ReposScreen(Widget):
    def compose(self) -> ComposeResult:
        yield Label("All Repositories", classes="section-header")
        yield DataTable(id="repo-table-full", cursor_type="row")

    def on_mount(self):
        table = self.query_one("#repo-table-full", DataTable)
        table.add_columns("Name", "Branch", "Path", "Dirty", "A", "B", "Commit", "Remote")

    def refresh_data(self, data: WorkspaceData):
        table = self.query_one("#repo-table-full", DataTable)
        table.clear()
        self._repos = data.repos
        for r in data.repos:
            dirty = "[yellow]●[/]" if r.dirty else "[green]✓[/]"
            ahead = str(r.ahead) if r.ahead else ""
            behind = str(r.behind) if r.behind else ""
            commit = r.last_commit_msg[:30] + "..." if len(r.last_commit_msg) > 30 else r.last_commit_msg
            remote = r.remote_url.split("/")[-1] if r.remote_url else ""
            branch = r.branch if r.branch else "[dim]detached[/]"
            path = r.path if len(r.path) < 35 else "..." + r.path[-32:]
            if not r.exists:
                table.add_row(f"[red]{r.name}[/]", "[red]missing[/]", "", "", "", "", "", "")
            else:
                table.add_row(r.name, branch, f"[dim]{path}[/]", dirty, ahead, behind, f"[dim]{commit}[/]", f"[dim]{remote}[/]")

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        if hasattr(self, "_repos") and event.cursor_row is not None:
            if 0 <= event.cursor_row < len(self._repos):
                self.app.push_screen(RepoDetail(self._repos[event.cursor_row]))
