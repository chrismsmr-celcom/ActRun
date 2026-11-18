import { useMemo, useState } from "react";
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowRight, ArrowUpRight, Bot,
  Boxes, Check, ChevronDown, CircleHelp, Clock3, Command, GitBranch,
  LayoutDashboard, LockKeyhole, Menu, Moon, MoreHorizontal, Network,
  Plus, Search, Settings2, ShieldCheck, Sun, TerminalSquare, Workflow, X,
  Zap, Filter, RefreshCw, Cpu, Timer, ChevronRight, CircleDot
} from "lucide-react";

type Page = "Overview" | "Agents" | "Tasks" | "Shared state" | "Leases" | "Conflicts" | "Event log" | "MCP server" | "Settings";

const primaryNav: { label: Page; icon: typeof LayoutDashboard; badge?: string }[] = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Agents", icon: Bot, badge: "5" },
  { label: "Tasks", icon: Workflow },
  { label: "Shared state", icon: Boxes },
  { label: "Leases", icon: LockKeyhole },
  { label: "Conflicts", icon: GitBranch, badge: "2" },
  { label: "Event log", icon: Activity },
];
const systemNav: { label: Page; icon: typeof LayoutDashboard }[] = [
  { label: "MCP server", icon: TerminalSquare },
  { label: "Settings", icon: Settings2 },
];

const activities = [
  { icon: Check, tone: "success", title: "Lease acquired", detail: "agent-backend · shared/api-schema", time: "2 min ago" },
  { icon: GitBranch, tone: "warning", title: "Merge conflict detected", detail: "agent-frontend · src/routes.ts", time: "8 min ago" },
  { icon: Check, tone: "success", title: "State committed", detail: "agent-tests · test-results", time: "14 min ago" },
  { icon: LockKeyhole, tone: "neutral", title: "Lease released", detail: "agent-database · shared/users", time: "21 min ago" },
];

const agents = [
  { name: "agent-backend", role: "Backend implementation", status: "Working", task: "Implement API routes", color: "violet", initials: "BE" },
  { name: "agent-frontend", role: "Frontend implementation", status: "Needs review", task: "Update application shell", color: "blue", initials: "FE" },
  { name: "agent-database", role: "Database operations", status: "Idle", task: "—", color: "green", initials: "DB" },
  { name: "agent-tests", role: "QA & testing", status: "Working", task: "Run integration suite", color: "orange", initials: "QA" },
];

const pageDescriptions: Record<Page, string> = {
  Overview: "A live view of your agent workspace and coordination activity.",
  Agents: "Monitor the agents participating in this workspace.",
  Tasks: "Track work assigned across your agent cohort.",
  "Shared state": "Inspect the shared data your agents read and update.",
  Leases: "See which agent currently owns each shared resource.",
  Conflicts: "Review concurrent updates that need a resolution.",
  "Event log": "An ordered history of coordination events.",
  "MCP server": "Connect AI clients to the Cohort coordination tools.",
  Settings: "Configure this workspace and its runtime.",
};

function App() {
  const [page, setPage] = useState<Page>("Overview");
  const [dark, setDark] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [notice, setNotice] = useState("");

  const notify = (message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 2800);
  };

  const pageContent = useMemo(() => {
    if (page === "Overview") return <Overview onNavigate={setPage} onCreate={() => setShowCreate(true)} />;
    if (page === "Agents") return <AgentsPage onNotify={notify} />;
    return <PlaceholderPage page={page} onAction={() => notify(`${page} controls will be connected in a later step.`)} />;
  }, [page]);

  return (
    <div className={dark ? "app-shell dark" : "app-shell light"}>
      {mobileOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
      <aside className={mobileOpen ? "sidebar mobile-visible" : "sidebar"}>
        <div className="brand-row">
          <div className="brand-mark"><Network size={19} strokeWidth={2.1} /></div>
          <div className="brand-copy"><strong>cerbere<span>.</span></strong><small>COHORT</small></div>
          <button className="icon-button mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close menu"><X size={18} /></button>
        </div>
        <button className="workspace-switch" onClick={() => notify("Workspace switching will be available when workspace management is connected.")}>
          <div className="workspace-avatar">C</div>
          <div className="workspace-meta"><strong>Personal workspace</strong><span>Local environment</span></div>
          <ChevronDown size={15} />
        </button>
        <div className="nav-label">WORKSPACE</div>
        <nav className="nav-list">
          {primaryNav.map(item => <NavItem key={item.label} item={item} active={page === item.label} onClick={() => { setPage(item.label); setMobileOpen(false); }} />)}
        </nav>
        <div className="nav-label system-label">SYSTEM</div>
        <nav className="nav-list">
          {systemNav.map(item => <NavItem key={item.label} item={item} active={page === item.label} onClick={() => { setPage(item.label); setMobileOpen(false); }} />)}
        </nav>
        <div className="sidebar-bottom">
          <div className="runtime-card">
            <div className="runtime-top"><span className="status-dot" /> Local runtime <span className="runtime-state">DEMO</span></div>
            <p>Connected interface preview. Runtime data is not connected yet.</p>
            <div className="runtime-link"><span>Connection status</span><strong>Not connected</strong></div>
          </div>
          <button className="profile-row" onClick={() => setPage("Settings")}>
            <div className="profile-avatar">CC</div><div><strong>Workspace owner</strong><span>Administrator</span></div><MoreHorizontal size={17} />
          </button>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button className="icon-button mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open menu"><Menu size={19} /></button>
            <div className="breadcrumbs"><span>Workspace</span><span className="crumb-slash">/</span><strong>{page}</strong></div>
          </div>
          <div className="topbar-actions">
            <label className="search-box"><Search size={16} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search anything..." /><kbd>⌘ K</kbd></label>
            <span className="topbar-divider" />
            <button className="icon-button theme-toggle" onClick={() => setDark(!dark)} aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}>{dark ? <Sun size={17} /> : <Moon size={17} />}</button>
            <button className="help-button" onClick={() => notify("Documentation links will be added here.")}><CircleHelp size={17} /></button>
          </div>
        </header>

        <div className="content-wrap">
          <div className="page-heading">
            <div><div className="eyebrow">CERBERE COHORT <span> / </span> CONTROL PLANE</div><h1>{page}</h1><p>{pageDescriptions[page]}</p></div>
            <div className="heading-actions"><span className="preview-pill"><span className="preview-dot" /> UI PREVIEW</span>{page === "Overview" && <button className="primary-button" onClick={() => setShowCreate(true)}><Plus size={16} /> New task</button>}</div>
          </div>
          {search && <div className="search-feedback">Search is a visual placeholder for now. Query: <strong>{search}</strong><button onClick={() => setSearch("")}>Clear</button></div>}
          {pageContent}
          <footer className="page-footer"><span>© 2026 Cerbere Cohort</span><span>Built for reliable multi-agent coordination</span><span className="version-label">PREVIEW · v0.1</span></footer>
        </div>
      </main>

      {showCreate && <div className="modal-backdrop" onClick={() => setShowCreate(false)}><div className="modal" onClick={e => e.stopPropagation()}><div className="modal-head"><div><span className="eyebrow">WORKSPACE ACTION</span><h2>Create a task</h2></div><button className="icon-button" onClick={() => setShowCreate(false)}><X size={18} /></button></div><p className="modal-copy">Task creation is not connected to the runtime yet. This form previews the intended workflow.</p><label className="field-label">Task name<input placeholder="e.g. Implement authentication flow" /></label><label className="field-label">Assign to<select defaultValue=""><option value="" disabled>Select an agent</option>{agents.map(a => <option key={a.name}>{a.name}</option>)}</select></label><div className="modal-actions"><button className="secondary-button" onClick={() => setShowCreate(false)}>Cancel</button><button className="primary-button" onClick={() => { setShowCreate(false); notify("Task creation is a UI preview and has not been saved."); }}>Preview action <ArrowRight size={15} /></button></div></div></div>}
      {notice && <div className="toast"><Check size={16} />{notice}</div>}
    </div>
  );
}

function NavItem({ item, active, onClick }: { item: { label: Page; icon: typeof LayoutDashboard; badge?: string }; active: boolean; onClick: () => void }) {
  const Icon = item.icon;
  return <button className={active ? "nav-item active" : "nav-item"} onClick={onClick}><Icon size={17} strokeWidth={1.8} /><span>{item.label}</span>{item.badge && <small>{item.badge}</small>}</button>;
}

function Overview({ onNavigate, onCreate }: { onNavigate: (page: Page) => void; onCreate: () => void }) {
  return <>
    <section className="welcome-strip"><div className="welcome-icon"><Zap size={19} /></div><div><strong>Your coordination workspace</strong><p>This is a sample dashboard. Connect the Cohort runtime to replace demo values with live data.</p></div><span className="demo-tag">SAMPLE DATA</span></section>
    <section className="stats-grid">
      <StatCard label="Registered agents" value="05" delta="4 active in sample" icon={Bot} tone="violet" trend="up" />
      <StatCard label="Tasks in progress" value="08" delta="3 awaiting assignment" icon={Workflow} tone="blue" trend="up" />
      <StatCard label="Active leases" value="03" delta="Across 3 resources" icon={LockKeyhole} tone="green" trend="neutral" />
      <StatCard label="Open conflicts" value="02" delta="Requires attention" icon={AlertTriangle} tone="orange" trend="down" />
    </section>
    <section className="dashboard-grid">
      <div className="panel execution-panel">
        <div className="panel-heading"><div><h2>Coordination overview</h2><p>How work moves through your cohort</p></div><button className="subtle-button" onClick={() => onNavigate("Event log")}>View events <ArrowRight size={14} /></button></div>
        <div className="flow-track">
          <FlowNode icon={Bot} title="Agents" value="05 registered" tone="violet" />
          <div className="flow-connector"><span /></div>
          <FlowNode icon={Boxes} title="Shared state" value="12 keys tracked" tone="blue" />
          <div className="flow-connector"><span /></div>
          <FlowNode icon={GitBranch} title="Coordination" value="Conflict-aware" tone="green" />
          <div className="flow-connector"><span /></div>
          <FlowNode icon={Check} title="Commits" value="24 recorded" tone="orange" />
        </div>
        <div className="panel-footnote"><span className="status-dot" /> Coordination pipeline <strong>Ready for runtime connection</strong></div>
      </div>
      <div className="panel health-panel">
        <div className="panel-heading"><div><h2>Workspace health</h2><p>Runtime status snapshot</p></div><MoreHorizontal size={18} className="muted-icon" /></div>
        <div className="health-score"><div className="health-ring"><ShieldCheck size={25} /></div><div><strong>—</strong><span>No live score yet</span></div></div>
        <div className="health-list"><div><span>Runtime connection</span><b className="state-neutral">Not connected</b></div><div><span>Lease manager</span><b className="state-neutral">Preview</b></div><div><span>Event stream</span><b className="state-neutral">Preview</b></div></div>
      </div>
    </section>
    <section className="lower-grid">
      <div className="panel agents-panel">
        <div className="panel-heading"><div><h2>Agent activity</h2><p>Agents in this workspace</p></div><button className="subtle-button" onClick={() => onNavigate("Agents")}>All agents <ArrowRight size={14} /></button></div>
        <div className="agent-table"><div className="table-head"><span>AGENT</span><span>STATUS</span><span>CURRENT TASK</span><span /></div>
          {agents.slice(0, 4).map(a => <div className="agent-row" key={a.name}><div className="agent-identity"><div className={`agent-avatar ${a.color}`}>{a.initials}</div><div><strong>{a.name}</strong><span>{a.role}</span></div></div><div><Status status={a.status} /></div><div className="task-cell">{a.task}</div><button className="row-more" aria-label={`More about ${a.name}`}><MoreHorizontal size={17} /></button></div>)}
        </div>
      </div>
      <div className="panel activity-panel">
        <div className="panel-heading"><div><h2>Recent activity</h2><p>Latest coordination events</p></div><button className="icon-button small-icon" onClick={() => onNavigate("Event log")} aria-label="Open event log"><ArrowUpRight size={16} /></button></div>
        <div className="activity-list">{activities.map((a, i) => { const Icon = a.icon; return <div className="activity-item" key={i}><div className={`activity-icon ${a.tone}`}><Icon size={15} /></div><div className="activity-copy"><strong>{a.title}</strong><span>{a.detail}</span></div><time>{a.time}</time></div>; })}</div>
        <button className="activity-link" onClick={() => onNavigate("Event log")}>Open event log <ArrowRight size={14} /></button>
      </div>
    </section>
    <section className="bottom-callout"><div className="callout-icon"><Command size={18} /></div><div><strong>Bring your agents into one coordinated workspace</strong><p>Connect your MCP client to expose shared state, leases and conflict-aware updates.</p></div><button className="secondary-button" onClick={() => onNavigate("MCP server")}>Explore MCP setup <ArrowRight size={14} /></button></section>
  </>;
}

function StatCard({ label, value, delta, icon: Icon, tone, trend }: { label: string; value: string; delta: string; icon: typeof Bot; tone: string; trend: string }) {
  return <div className="stat-card"><div className="stat-top"><span>{label}</span><div className={`stat-icon ${tone}`}><Icon size={17} /></div></div><div className="stat-value">{value}</div><div className="stat-bottom"><span className={trend === "down" ? "trend down" : "trend"}>{trend === "up" ? <ArrowUpRight size={13} /> : trend === "down" ? <ArrowDownRight size={13} /> : <Activity size={12} />}{delta}</span></div></div>;
}

function FlowNode({ icon: Icon, title, value, tone }: { icon: typeof Bot; title: string; value: string; tone: string }) {
  return <div className="flow-node"><div className={`flow-icon ${tone}`}><Icon size={18} /></div><strong>{title}</strong><span>{value}</span></div>;
}

function Status({ status }: { status: string }) {
  const cls = status === "Working" ? "working" : status === "Needs review" ? "review" : "idle";
  return <span className={`status-badge ${cls}`}><i />{status}</span>;
}


function AgentsPage({ onNotify }: { onNotify: (message: string) => void }) {
  const [filter, setFilter] = useState("All agents");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<(typeof agents)[number] | null>(null);
  const filtered = agents.filter(agent => {
    const matchesFilter = filter === "All agents" ||
      (filter === "Working" && agent.status === "Working") ||
      (filter === "Idle" && agent.status === "Idle") ||
      (filter === "Needs review" && agent.status === "Needs review");
    const matchesQuery = `${agent.name} ${agent.role} ${agent.task}`.toLowerCase().includes(query.toLowerCase());
    return matchesFilter && matchesQuery;
  });

  return <>
    <section className="agents-summary">
      <div className="agents-summary-copy"><div className="summary-icon"><Bot size={20}/></div><div><strong>Agent registry</strong><p>One place to inspect the agents participating in this workspace.</p></div></div>
      <span className="sample-data-label"><span/> SAMPLE DATA</span>
    </section>
    <section className="agent-metrics">
      <div className="agent-metric"><span>Total agents</span><strong>05</strong><small>Registered in workspace</small></div>
      <div className="agent-metric"><span>Working</span><strong className="metric-green">02</strong><small>Currently executing tasks</small></div>
      <div className="agent-metric"><span>Needs review</span><strong className="metric-amber">01</strong><small>Waiting for attention</small></div>
      <div className="agent-metric"><span>Idle</span><strong>02</strong><small>Available for assignment</small></div>
    </section>
    <section className="panel agent-registry-panel">
      <div className="registry-toolbar">
        <div><h2>All agents <span className="count-chip">{filtered.length}</span></h2><p>Inspect status, workload and runtime identity.</p></div>
        <button className="secondary-button" onClick={() => onNotify("Agent registration will be connected to the runtime later.")}><Plus size={15}/> Register agent</button>
      </div>
      <div className="registry-controls">
        <label className="registry-search"><Search size={15}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Find an agent..."/></label>
        <div className="filter-control"><Filter size={14}/><select value={filter} onChange={e=>setFilter(e.target.value)}><option>All agents</option><option>Working</option><option>Idle</option><option>Needs review</option></select><ChevronDown size={13}/></div>
        <button className="icon-button refresh-button" onClick={()=>onNotify("Sample agent list refreshed. No runtime is connected.")} aria-label="Refresh agent list"><RefreshCw size={15}/></button>
      </div>
      <div className="registry-table">
        <div className="registry-table-head"><span>AGENT</span><span>STATUS</span><span>ASSIGNED WORK</span><span>LAST ACTIVITY</span><span/></div>
        {filtered.map((agent,index)=><button className="registry-row" key={agent.name} onClick={()=>setSelected(agent)}>
          <div className="registry-agent"><div className={`agent-avatar ${agent.color}`}>{agent.initials}</div><div><strong>{agent.name}</strong><span>{agent.role}</span></div></div>
          <div><Status status={agent.status}/></div>
          <div className="registry-task"><span>{agent.task}</span><small>{agent.status==="Idle"?"No active task":"1 task assigned"}</small></div>
          <div className="last-activity"><span className="activity-pulse"/>{index===0?"Just now":index===1?"4 min ago":index===2?"12 min ago":"18 min ago"}</div>
          <ChevronRight size={16} className="registry-chevron"/>
        </button>)}
        {filtered.length===0&&<div className="registry-empty"><Search size={20}/><strong>No agents found</strong><span>Try another name or status filter.</span></div>}
      </div>
      <div className="registry-footer"><span>Showing {filtered.length} of 5 sample agents</span><span>Live updates unavailable in preview</span></div>
    </section>
    <section className="agent-note"><div><Cpu size={17}/></div><p><strong>Agent identity is separate from agent activity.</strong><br/>When connected, this view will show registered identities, heartbeat state, assigned work and execution metadata from the Cohort runtime.</p></section>
    {selected&&<div className="modal-backdrop" onClick={()=>setSelected(null)}><div className="agent-detail-modal" onClick={e=>e.stopPropagation()}>
      <div className="agent-detail-head"><div className={`agent-avatar large ${selected.color}`}>{selected.initials}</div><div><span className="eyebrow">AGENT DETAILS · SAMPLE</span><h2>{selected.name}</h2><p>{selected.role}</p></div><button className="icon-button" onClick={()=>setSelected(null)} aria-label="Close agent details"><X size={18}/></button></div>
      <div className="detail-status-row"><Status status={selected.status}/><span><CircleDot size={12}/> Local preview identity</span></div>
      <div className="detail-grid"><div><span>Current task</span><strong>{selected.task}</strong></div><div><span>Heartbeat</span><strong>Not connected</strong></div><div><span>Agent ID</span><strong className="mono-value">agt_demo_{selected.initials.toLowerCase()}</strong></div><div><span>Last activity</span><strong>Sample timestamp</strong></div></div>
      <div className="detail-info"><Timer size={15}/><span>Runtime telemetry, token usage and tool execution history will appear after integration.</span></div>
      <div className="modal-actions"><button className="secondary-button" onClick={()=>setSelected(null)}>Close</button><button className="primary-button" onClick={()=>{setSelected(null);onNotify("Agent actions will be enabled after runtime integration.");}}>Agent actions <ArrowRight size={14}/></button></div>
    </div></div>}
  </>;
}

function PlaceholderPage({ page, onAction }: { page: Page; onAction: () => void }) {
  const configs: Record<Page, { icon: typeof Bot; title: string; body: string; cards: string[] }> = {
    Overview: { icon: LayoutDashboard, title: "", body: "", cards: [] },
    Agents: { icon: Bot, title: "Agent registry", body: "Your agent inventory will appear here once the runtime is connected.", cards: ["Agent identity & role", "Current task and status", "Last heartbeat"] },
    Tasks: { icon: Workflow, title: "Task orchestration", body: "Create, assign and follow work across your agents.", cards: ["Task assignment", "Execution status", "Dependencies"] },
    "Shared state": { icon: Boxes, title: "Shared workspace state", body: "Browse versioned keys and inspect the latest committed values.", cards: ["Key browser", "Version history", "Commit provenance"] },
    Leases: { icon: LockKeyhole, title: "Lease manager", body: "Understand resource ownership and prevent concurrent writes.", cards: ["Active lease ownership", "Expiry and renewal", "Fencing tokens"] },
    Conflicts: { icon: GitBranch, title: "Conflict resolution", body: "Review competing changes before they are committed.", cards: ["Conflicting keys", "Base / ours / theirs", "Resolution decisions"] },
    "Event log": { icon: Activity, title: "Coordination event stream", body: "Trace agent actions and understand how shared state changed over time.", cards: ["Event timeline", "Agent and action filters", "Event payload inspection"] },
    "MCP server": { icon: TerminalSquare, title: "MCP connection", body: "Expose Cohort tools to compatible AI clients through the Model Context Protocol.", cards: ["Server endpoint", "Available tools", "Client configuration"] },
    Settings: { icon: Settings2, title: "Workspace settings", body: "Manage workspace preferences and runtime configuration.", cards: ["Workspace profile", "Runtime connection", "Appearance"] },
  };
  const config = configs[page]; const Icon = config.icon;
  return <div className="placeholder-layout"><div className="panel placeholder-main"><div className="placeholder-icon"><Icon size={25} /></div><span className="eyebrow">COMING ONLINE IN STAGES</span><h2>{config.title}</h2><p>{config.body}</p><div className="feature-list">{config.cards.map((c, i) => <div key={c}><span className="feature-check"><Check size={13} /></span>{c}<span className="feature-state">Planned</span></div>)}</div><button className="primary-button" onClick={onAction}>Explore preview <ArrowRight size={15} /></button></div><div className="panel placeholder-side"><div className="side-orbit"><div className="orbit-core"><Icon size={24} /></div><span className="orbit-dot one" /><span className="orbit-dot two" /><span className="orbit-dot three" /></div><h3>One coordination layer.</h3><p>Shared context, clear ownership and safer concurrent work for AI agents.</p><div className="coming-note"><Clock3 size={14} /> This section will be connected progressively.</div></div></div>;
}

export default App;