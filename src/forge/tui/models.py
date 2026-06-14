from dataclasses import dataclass, field


@dataclass
class RepoRow:
    name: str
    branch: str
    path: str
    dirty: bool
    ahead: int
    behind: int
    last_commit_msg: str
    last_commit_time: str
    exists: bool
    has_remote: bool
    remote_url: str


@dataclass
class CVERow:
    vuln_id: str
    severity: str
    package: str
    version: str
    ecosystem: str
    summary: str
    cvss_score: float | None


@dataclass
class SessionRow:
    session_id: str
    agent: str
    feature: str
    started: str
    context: str
    elapsed: str


@dataclass
class FeatureRow:
    name: str
    feature_id: str
    repo_count: int
    repo_done: int
    created: str


@dataclass
class EventRow:
    timestamp: str
    command: str
    result: str


@dataclass
class WorkspaceData:
    repos: list[RepoRow] = field(default_factory=list)
    cves: list[CVERow] = field(default_factory=list)
    sessions: list[SessionRow] = field(default_factory=list)
    features: list[FeatureRow] = field(default_factory=list)
    health: dict = field(default_factory=dict)
    overall: dict = field(default_factory=dict)
    events: list[EventRow] = field(default_factory=list)
