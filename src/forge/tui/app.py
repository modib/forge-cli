import datetime
import subprocess
import sys

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, TabbedContent, TabPane


from .. import cve as forge_cve
from .. import engine
from .models import CVERow, EventRow, FeatureRow, RepoRow, SessionRow, WorkspaceData
from .screens.cves import CVEsScreen
from .screens.log import LogScreen
from .screens.overview import OverviewScreen
from .screens.repos import ReposScreen
from .screens.sessions import SessionsScreen


class TUIApp(App):
    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("f1", "switch_tab('overview')", "Overview", priority=True),
        Binding("f2", "switch_tab('repos')", "Repos", priority=True),
        Binding("f3", "switch_tab('cves')", "CVEs", priority=True),
        Binding("f4", "switch_tab('sessions')", "Sessions", priority=True),
        Binding("f5", "switch_tab('log')", "Log", priority=True),
        Binding("ctrl+r", "refresh", "Refresh", priority=True),
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("/", "focus_input", "Cmd", priority=True),
    ]

    _events: list[EventRow] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="overview"):
            with TabPane("Overview", id="overview"):
                yield OverviewScreen()
            with TabPane("Repos", id="repos"):
                yield ReposScreen()
            with TabPane("CVEs", id="cves"):
                yield CVEsScreen()
            with TabPane("Sessions", id="sessions"):
                yield SessionsScreen()
            with TabPane("Log", id="log"):
                yield LogScreen()
        yield Input(id="command-input", placeholder=">  forge exec ...  |  !shell command")
        yield Footer()

    def on_mount(self):
        self.set_interval(30, self.action_refresh)
        self.action_refresh()

    def _now(self) -> str:
        return datetime.datetime.now().strftime("%H:%M:%S")

    def action_focus_input(self):
        self.query_one("#command-input", Input).focus()

    def action_switch_tab(self, tab: str):
        tc = self.query_one(TabbedContent)
        tc.active = tab

    def action_refresh(self):
        self.run_worker(self._load_data(), exclusive=True)

    async def _load_data(self):
        self.sub_title = "Refreshing..."
        try:
            statuses = engine.get_status()
            overall = engine.get_overall_status()
            cves = forge_cve.list_cves() or []
            raw_sessions = engine.list_sessions(limit=20) or []
            from .. import config as cfg
            c = cfg.load_config()
            raw_features = c.get("features", [])
            health = engine.health_check()
        except Exception:
            import traceback
            self.sub_title = "[red]Error loading data[/]"
            sys.stderr.write(traceback.format_exc())
            return

        repos = []
        for r in statuses:
            repos.append(RepoRow(
                name=r.get("name", "?"),
                branch=r.get("branch", "?"),
                path=r.get("path", ""),
                dirty=r.get("dirty", False),
                ahead=r.get("ahead", 0),
                behind=r.get("behind", 0),
                last_commit_msg=r.get("last_commit_msg", ""),
                last_commit_time=r.get("last_commit_time", ""),
                exists=r.get("exists", True),
                has_remote=r.get("has_remote", False),
                remote_url=r.get("remote_url", ""),
            ))

        cve_rows = []
        for v in cves:
            sev = "unknown"
            score = v.get("cvss_score")
            if score is not None:
                if score >= 9.0:
                    sev = "critical"
                elif score >= 7.0:
                    sev = "high"
                elif score >= 4.0:
                    sev = "moderate"
                elif score > 0:
                    sev = "low"
            cve_rows.append(CVERow(
                vuln_id=v.get("id", "?"),
                severity=sev,
                package=v.get("package", "?"),
                version=v.get("version", ""),
                ecosystem=v.get("ecosystem", ""),
                summary=v.get("summary", ""),
                cvss_score=score,
            ))

        session_rows = []
        now = datetime.datetime.now(datetime.timezone.utc)
        for s in raw_sessions:
            elapsed = ""
            started_str = s.get("started", "")
            if started_str:
                try:
                    started = datetime.datetime.fromisoformat(started_str)
                    diff = now - started
                    mins = int(diff.total_seconds() // 60)
                    if mins < 1:
                        elapsed = "just now"
                    elif mins < 60:
                        elapsed = f"{mins}m ago"
                    else:
                        hours = mins // 60
                        elapsed = f"{hours}h {mins % 60}m ago"
                except ValueError:
                    elapsed = started_str
            session_rows.append(SessionRow(
                session_id=s.get("id", "?"),
                agent=s.get("agent", "?"),
                feature=s.get("feature", ""),
                started=started_str,
                context=s.get("context_preview", ""),
                elapsed=elapsed,
            ))

        feature_rows = []
        for f in raw_features:
            feature_rows.append(FeatureRow(
                name=f.get("name", "?"),
                feature_id=f.get("id", "?"),
                repo_count=len(f.get("repos", [])),
                repo_done=len(f.get("worktrees", {})),
                created=f.get("created", ""),
            ))

        data = WorkspaceData(
            repos=repos,
            cves=cve_rows,
            sessions=session_rows,
            features=feature_rows,
            health=health,
            overall=overall,
            events=self._events,
        )

        tc = self.query_one(TabbedContent)
        for pane in tc.query(TabPane):
            if pane.children:
                screen = pane.children[0]
                if hasattr(screen, "refresh_data"):
                    screen.refresh_data(data)

        now_str = self._now()
        dirty_count = overall.get("dirty", 0)
        repo_count = overall.get("total_repos", 0)
        cve_count = len(cves)
        health_str = self._format_health(health)
        summary = f"{repo_count} repos  |  {dirty_count} dirty  |  {cve_count} CVEs  |  {health_str}"
        self.sub_title = f"Updated {now_str}  —  {summary}"

    def _format_health(self, health: dict) -> str:
        parts = []
        for tool in ("ollama", "gh"):
            available = health.get(tool, False)
            mark = "\u2713" if available else "\u2717"
            parts.append(f"{tool} {mark}")
        disk = health.get("disk_used_pct", 0)
        parts.append(f"disk {disk}%")
        return "  ".join(parts)

    def on_input_submitted(self, event: Input.Submitted):
        query = event.value.strip()
        if not query:
            return
        self.query_one("#command-input", Input).value = ""
        ts = self._now()
        if query.startswith("!"):
            cmd = query[1:]
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                output = r.stdout.strip() or r.stderr.strip() or f"(exit code {r.returncode})"
            except subprocess.TimeoutExpired:
                output = "(timed out)"
            except Exception as e:
                output = str(e)
            self._events.append(EventRow(timestamp=ts, command=f"!{cmd}", result=output[:300]))
        else:
            from ..ai import exec_nl
            try:
                result = exec_nl(query)
                output = result.get("output", "") or result.get("command", "")
                if result.get("resolved_by"):
                    output = f"[dim]({result['resolved_by']})[/] {output}"
            except Exception as e:
                output = str(e)
            self._events.append(EventRow(timestamp=ts, command=f"> {query}", result=str(output)[:300]))

        tc = self.query_one(TabbedContent)
        for pane in tc.query(TabPane):
            if pane.id == "log" and pane.children:
                log_screen = pane.children[0]
                if hasattr(log_screen, "append_entry"):
                    log_screen.append_entry(f"> {query}", output[:200], timestamp=ts)

        self.action_refresh()
