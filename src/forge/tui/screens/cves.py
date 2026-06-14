from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import DataTable, Label, RichLog, Button
from textual.containers import Vertical, Horizontal
from ..models import WorkspaceData, CVERow


class CveDetail(ModalScreen):
    def __init__(self, cve: CVERow, full_detail: dict | None = None):
        super().__init__()
        self.cve = cve
        self.full_detail = full_detail

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"[bold]{self.cve.vuln_id}[/]", classes="section-header")
            yield RichLog(id="cve-detail-content", highlight=True, markup=True)
            with Horizontal():
                yield Button("Close", variant="primary", id="close-detail")

    def on_mount(self):
        log = self.query_one("#cve-detail-content", RichLog)
        c = self.cve
        log.write(f"Package:  {c.package}@{c.version}  ({c.ecosystem})")
        color = "red" if c.severity == "critical" else "yellow" if c.severity == "high" else "green" if c.severity == "moderate" else "dim"
        log.write(f"Severity: [{color}]{c.severity.upper()}[/]")
        score = f"{c.cvss_score:.1f}" if c.cvss_score is not None else "[dim]N/A[/]"
        log.write(f"CVSS:     {score}")
        log.write(f"Summary:  {c.summary}")
        if self.full_detail:
            log.write("")
            log.write("[bold]OSV.dev detail:[/]")
            log.write(str(self.full_detail))

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "close-detail":
            self.app.pop_screen()


class CVEsScreen(Widget):
    def compose(self) -> ComposeResult:
        yield Label(id="cve-summary")
        yield DataTable(id="cve-table", cursor_type="row")

    def on_mount(self):
        table = self.query_one("#cve-table", DataTable)
        table.add_columns("Severity", "CVE ID", "Package", "Version", "Eco", "Summary")

    def refresh_data(self, data: WorkspaceData):
        table = self.query_one("#cve-table", DataTable)
        table.clear()
        self._cves = data.cves
        by_sev: dict[str, int] = {}
        for c in data.cves:
            by_sev[c.severity] = by_sev.get(c.severity, 0) + 1
        summary_parts = []
        for sev, color in (("critical", "red"), ("high", "yellow"), ("moderate", "green"), ("low", "dim"), ("unknown", "dim")):
            count = by_sev.get(sev, 0)
            if count:
                summary_parts.append(f"[{color}]{count} {sev}[/]")
        summary_text = f"{len(data.cves)} vulns —  {'  '.join(summary_parts)}" if summary_parts else "[dim]No CVEs[/]"
        self.query_one("#cve-summary", Label).update(summary_text)

        for c in data.cves:
            color = "red" if c.severity == "critical" else "yellow" if c.severity == "high" else "green" if c.severity == "moderate" else "dim"
            table.add_row(
                f"[{color}]{c.severity.upper()}[/]",
                c.vuln_id,
                c.package,
                c.version,
                c.ecosystem,
                c.summary[:50],
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        if hasattr(self, "_cves") and event.cursor_row is not None:
            if 0 <= event.cursor_row < len(self._cves):
                self.app.push_screen(CveDetail(self._cves[event.cursor_row]))
