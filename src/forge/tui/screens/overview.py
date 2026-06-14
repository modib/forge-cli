from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable, Label, ListView, ListItem, RichLog
from textual.containers import Horizontal, Vertical
from ..models import WorkspaceData


class OverviewScreen(Widget):
    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="overview-left"):
                yield Label("Repos", classes="section-header")
                yield DataTable(id="repo-table-overview", cursor_type="row")
                yield Label("Features", classes="section-header")
                yield ListView(id="feature-list")
            with Vertical(id="overview-right"):
                yield Label("CVE Alerts", classes="section-header")
                yield ListView(id="cve-list")
                yield Label("Active Sessions", classes="section-header")
                yield ListView(id="session-list")
        yield RichLog(id="overview-log", highlight=True, markup=True, max_lines=5)

    def on_mount(self):
        table = self.query_one("#repo-table-overview", DataTable)
        table.add_columns("Name", "Branch", "Dirty", "A", "B")

    def refresh_data(self, data: WorkspaceData):
        self._update_repo_table(data.repos)
        self._update_feature_list(data.features)
        self._update_cve_list(data.cves)
        self._update_session_list(data.sessions)
        self._update_log(data.events)

    def _update_repo_table(self, repos):
        table = self.query_one("#repo-table-overview", DataTable)
        table.clear()
        for r in repos:
            dirty = "[yellow]● dirty[/]" if r.dirty else "[green]✓[/]"
            ahead = f"[green]+{r.ahead}[/]" if r.ahead else ""
            behind = f"[red]-{r.behind}[/]" if r.behind else ""
            branch = r.branch if r.branch else "[dim]detached[/]"
            if not r.exists:
                table.add_row(f"[red]{r.name}[/]", "[red]missing[/]", "", "", "")
            else:
                table.add_row(r.name, branch, dirty, ahead, behind)

    def _update_feature_list(self, features):
        lv = self.query_one("#feature-list", ListView)
        lv.clear()
        if not features:
            lv.append(ListItem(Label("[dim]No active features[/]")))
            return
        for f in features:
            label = Label(f"{f.name}  [dim]({f.repo_done}/{f.repo_count} repos)[/]")
            lv.append(ListItem(label))

    def _update_cve_list(self, cves):
        lv = self.query_one("#cve-list", ListView)
        lv.clear()
        if not cves:
            lv.append(ListItem(Label("[dim]No CVEs found[/]")))
            return
        for c in cves:
            color = "red" if c.severity == "critical" else "yellow" if c.severity == "high" else "green" if c.severity == "moderate" else "dim"
            label_str = f"[{color}]{c.vuln_id}[/]  {c.package}  [dim]{c.summary[:60]}[/]"
            lv.append(ListItem(Label(label_str)))

    def _update_session_list(self, sessions):
        lv = self.query_one("#session-list", ListView)
        lv.clear()
        if not sessions:
            lv.append(ListItem(Label("[dim]No active sessions[/]")))
            return
        for s in sessions:
            feat = f"({s.feature})" if s.feature else ""
            label = Label(f"{s.agent}  {s.session_id[:12]}  {feat}  [dim]{s.elapsed}[/]")
            lv.append(ListItem(label))

    def _update_log(self, events):
        log = self.query_one("#overview-log", RichLog)
        log.clear()
        if not events:
            log.write("[dim]No recent events[/]")
            return
        for e in events:
            log.write(f"[dim]{e.timestamp}[/] [bold]{e.command}[/]  {e.result}")
