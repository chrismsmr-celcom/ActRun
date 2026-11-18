import { useMemo, useState, type DragEvent } from "react";
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowRight, ArrowUpRight, Bot,
  Boxes, Check, ChevronDown, CircleHelp, Clock3, Command, GitBranch,
  LayoutDashboard, LockKeyhole, Menu, Moon, MoreHorizontal, Network,
  Plus, Search, Settings2, ShieldCheck, Sun, TerminalSquare, Workflow, X,
  Zap, Filter, RefreshCw, Cpu, Timer, ChevronRight, CircleDot,
  Database, History, Hash, FileJson, GitCommit, Pencil, Save, Eye
} from "lucide-react";

type Page = "Overview" | "Agents" | "Tasks" | "Branches" | "Shared state" | "Leases" | "Conflicts" | "Event log" | "MCP server" | "Settings";

const primaryNav: { label: Page; icon: typeof LayoutDashboard; badge?: string }[] = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Agents", icon: Bot, badge: "5" },
  { label: "Tasks", icon: Workflow },
  { label: "Branches", icon: GitBranch },
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
  { name: "agent-security", role: "Security review", status: "Idle", task: "—", color: "violet", initials: "SC" },
];

const pageDescriptions: Record<Page, string> = {
  Overview: "A live view of your agent workspace and coordination activity.",
  Agents: "Monitor the agents participating in this workspace.",
  Tasks: "Track work assigned across your agent cohort.",
  Branches: "Inspect isolated agent branches and review changes before merging.",
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
    if (page === "Tasks") return <TasksPage onNotify={notify} />;
    if (page === "Branches") return <BranchesPage onNotify={notify} />;
    if (page === "Leases") return <LeasesPage onNotify={notify} />;
    if (page === "Conflicts") return <ConflictsPage onNotify={notify} />;
    if (page === "Event log") return <EventLogPage />;
    if (page === "MCP server") return <McpPage onNotify={notify} />;
    if (page === "Settings") return <SettingsPage onNotify={notify} />;
    if (page === "Shared state") return <SharedStatePage onNotify={notify} />;
    return null;
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


type TaskStatus = "Backlog" | "Assigned" | "In progress" | "Review" | "Completed";
type TaskPriority = "Low" | "Medium" | "High" | "Urgent";
type CohortTask = { id: string; title: string; description: string; status: TaskStatus; priority: TaskPriority; assignee: string; due: string; dependencies: string[]; tags: string[] };
const taskColumns: { status: TaskStatus; tone: string }[] = [
  { status: "Backlog", tone: "slate" },
  { status: "Assigned", tone: "blue" },
  { status: "In progress", tone: "violet" },
  { status: "Review", tone: "amber" },
  { status: "Completed", tone: "green" },
];
const initialTasks: CohortTask[] = [
  { id:"TSK-041",title:"Define authentication API contract",description:"Agree on the authentication endpoints, request payloads and response schemas before implementation begins.",status:"Backlog",priority:"High",assignee:"Unassigned",due:"Nov 21",dependencies:[],tags:["API","Planning"] },
  { id:"TSK-042",title:"Prepare staging database schema",description:"Create the initial schema and migration plan for the staging environment.",status:"Backlog",priority:"Medium",assignee:"Unassigned",due:"Nov 22",dependencies:[],tags:["Database"] },
  { id:"TSK-038",title:"Implement user API routes",description:"Build the user endpoints and align them with the shared API schema.",status:"Assigned",priority:"High",assignee:"agent-backend",due:"Nov 20",dependencies:["TSK-041"],tags:["Backend","API"] },
  { id:"TSK-039",title:"Create application shell",description:"Implement the responsive application shell and connect the core navigation.",status:"Assigned",priority:"Medium",assignee:"agent-frontend",due:"Nov 23",dependencies:[],tags:["Frontend","UI"] },
  { id:"TSK-035",title:"Build shared state adapter",description:"Implement the adapter used by agents to read and write versioned shared state.",status:"In progress",priority:"Urgent",assignee:"agent-backend",due:"Nov 19",dependencies:["TSK-041"],tags:["Core","Shared state"] },
  { id:"TSK-036",title:"Run integration test suite",description:"Validate the API and shared-state flows against the current integration test suite.",status:"In progress",priority:"High",assignee:"agent-tests",due:"Nov 20",dependencies:["TSK-035"],tags:["QA","Testing"] },
  { id:"TSK-032",title:"Review route permissions",description:"Check route-level permissions and report any missing authorization checks.",status:"Review",priority:"High",assignee:"agent-security",due:"Nov 19",dependencies:["TSK-038"],tags:["Security"] },
  { id:"TSK-029",title:"Document workspace conventions",description:"Write the initial conventions for agent branches, shared keys and commit messages.",status:"Completed",priority:"Low",assignee:"agent-tests",due:"Nov 16",dependencies:[],tags:["Docs"] },
];

function TasksPage({ onNotify }: { onNotify: (message: string) => void }) {
  const [tasks, setTasks] = useState<CohortTask[]>(initialTasks);
  const [query, setQuery] = useState("");
  const [priority, setPriority] = useState("All priorities");
  const [selected, setSelected] = useState<CohortTask | null>(null);
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newAssignee, setNewAssignee] = useState("Unassigned");
  const [newPriority, setNewPriority] = useState<TaskPriority>("Medium");
  const [newDue, setNewDue] = useState("Nov 25");
  const filtered = tasks.filter(task => {
    const matchesText = `${task.id} ${task.title} ${task.assignee} ${task.tags.join(" ")}`.toLowerCase().includes(query.toLowerCase());
    return matchesText && (priority === "All priorities" || task.priority === priority);
  });
  const counts = (status: TaskStatus) => tasks.filter(task => task.status === status).length;
  const updateTask = (id: string, patch: Partial<CohortTask>) => {
    setTasks(current => current.map(task => task.id === id ? { ...task, ...patch } : task));
    setSelected(current => current?.id === id ? { ...current, ...patch } : current);
  };
  const createTask = () => {
    if (!newTitle.trim()) return;
    const task: CohortTask = { id:`TSK-${String(43 + tasks.length - initialTasks.length).padStart(3,"0")}`,title:newTitle.trim(),description:"New task created in the local interface preview.",status:newAssignee==="Unassigned"?"Backlog":"Assigned",priority:newPriority,assignee:newAssignee,due:newDue,dependencies:[],tags:["New"] };
    setTasks(current=>[task,...current]); setCreating(false); setNewTitle(""); onNotify("Task added to this local preview. It has not been saved to the runtime.");
  };
  const moveTask = (task: CohortTask, direction: -1 | 1) => {
    const index = taskColumns.findIndex(column=>column.status===task.status);
    const next = taskColumns[Math.max(0,Math.min(taskColumns.length-1,index+direction))].status;
    updateTask(task.id,{status:next});
  };
  const onDrop = (event: DragEvent<HTMLDivElement>, status: TaskStatus) => {
    const id=event.dataTransfer.getData("text/task-id");
    if(id) updateTask(id,{status});
  };

  return <>
    <section className="tasks-summary">
      <div className="tasks-summary-left"><div className="summary-icon"><Workflow size={20}/></div><div><strong>Task orchestration</strong><p>Coordinate work, ownership and dependencies across your agent cohort.</p></div></div>
      <span className="sample-data-label"><span/> SAMPLE DATA</span>
    </section>
    <section className="task-stats">
      <div><span>Total tasks</span><strong>{String(tasks.length).padStart(2,"0")}</strong><small>Across this workspace</small></div>
      <div><span>In progress</span><strong className="metric-violet">{String(counts("In progress")).padStart(2,"0")}</strong><small>Currently being executed</small></div>
      <div><span>In review</span><strong className="metric-amber">{String(counts("Review")).padStart(2,"0")}</strong><small>Awaiting verification</small></div>
      <div><span>Completed</span><strong className="metric-green">{String(counts("Completed")).padStart(2,"0")}</strong><small>Finished tasks</small></div>
    </section>
    <section className="panel task-board-panel">
      <div className="task-board-toolbar"><div><h2>Task board <span className="count-chip">{filtered.length} tasks</span></h2><p>Move cards between stages as work progresses.</p></div><button className="primary-button" onClick={()=>setCreating(true)}><Plus size={15}/> New task</button></div>
      <div className="task-filters"><label className="registry-search"><Search size={15}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search tasks..."/></label><div className="filter-control"><Filter size={14}/><select value={priority} onChange={e=>setPriority(e.target.value)}><option>All priorities</option><option>Urgent</option><option>High</option><option>Medium</option><option>Low</option></select><ChevronDown size={13}/></div><span className="drag-hint">Drag cards to change status</span></div>
      <div className="kanban-board">{taskColumns.map(column=>{
        const columnTasks=filtered.filter(task=>task.status===column.status);
        return <div className="kanban-column" key={column.status} onDragOver={e=>e.preventDefault()} onDrop={e=>onDrop(e,column.status)}>
          <div className="kanban-column-head"><div><span className={`column-indicator ${column.tone}`}/><strong>{column.status}</strong><small>{counts(column.status)}</small></div><button className="column-more" onClick={()=>onNotify(`Options for ${column.status} will be connected later.`)} aria-label={`More options for ${column.status}`}><MoreHorizontal size={16}/></button></div>
          <div className="kanban-cards">{columnTasks.map(task=><article className="task-card" key={task.id} draggable onDragStart={e=>e.dataTransfer.setData("text/task-id",task.id)} onClick={()=>setSelected(task)}>
            <div className="task-card-top"><span>{task.id}</span><PriorityBadge priority={task.priority}/></div>
            <h3>{task.title}</h3><p>{task.description}</p>
            <div className="task-tags">{task.tags.map(tag=><span key={tag}>{tag}</span>)}</div>
            {task.dependencies.length>0&&<div className="task-dependency"><GitBranch size={12}/> Depends on {task.dependencies.join(", ")}</div>}
            <div className="task-card-foot"><div className="task-assignee"><span className={`assignee-avatar ${task.assignee==="Unassigned"?"unassigned":task.assignee==="agent-backend"?"violet":task.assignee==="agent-frontend"?"blue":task.assignee==="agent-tests"?"orange":"green"}`}>{task.assignee==="Unassigned"?"—":task.assignee.split("-")[1]?.slice(0,2).toUpperCase()}</span><span>{task.assignee==="Unassigned"?"Unassigned":task.assignee}</span></div><span className="task-due"><Clock3 size={12}/>{task.due}</span></div>
            <div className="task-quick-actions"><button onClick={e=>{e.stopPropagation();moveTask(task,-1)}} disabled={column.status==="Backlog"}>←</button><button onClick={e=>{e.stopPropagation();moveTask(task,1)}} disabled={column.status==="Completed"}>→</button></div>
          </article>)}
          {columnTasks.length===0&&<div className="kanban-empty">No tasks in this stage</div>}
          </div>
          {column.status==="Backlog"&&<button className="add-task-inline" onClick={()=>setCreating(true)}><Plus size={14}/> Add a task</button>}
        </div>;
      })}</div>
      <div className="board-footnote"><span><i/> Local preview state</span><span>Changes are held in this browser session only. Runtime persistence is not connected.</span></div>
    </section>
    {creating&&<div className="modal-backdrop" onClick={()=>setCreating(false)}><div className="task-modal" onClick={e=>e.stopPropagation()}><div className="modal-head"><div><span className="eyebrow">TASK ORCHESTRATION</span><h2>Create a task</h2></div><button className="icon-button" onClick={()=>setCreating(false)}><X size={18}/></button></div><p className="modal-copy">Add a task to the local board preview. Backend persistence will be connected later.</p><label className="field-label">Task title<input autoFocus value={newTitle} onChange={e=>setNewTitle(e.target.value)} placeholder="What needs to be done?"/></label><div className="task-form-grid"><label className="field-label">Assign to<select value={newAssignee} onChange={e=>setNewAssignee(e.target.value)}><option>Unassigned</option>{agents.map(agent=><option key={agent.name}>{agent.name}</option>)}</select></label><label className="field-label">Priority<select value={newPriority} onChange={e=>setNewPriority(e.target.value as TaskPriority)}><option>Low</option><option>Medium</option><option>High</option><option>Urgent</option></select></label></div><label className="field-label">Due date<input value={newDue} onChange={e=>setNewDue(e.target.value)} placeholder="e.g. Nov 25"/></label><div className="modal-actions"><button className="secondary-button" onClick={()=>setCreating(false)}>Cancel</button><button className="primary-button" disabled={!newTitle.trim()} onClick={createTask}>Create task <ArrowRight size={14}/></button></div></div></div>}
    {selected&&<div className="modal-backdrop" onClick={()=>setSelected(null)}><div className="task-modal task-detail-modal" onClick={e=>e.stopPropagation()}><div className="modal-head"><div><span className="eyebrow">{selected.id} · TASK DETAILS</span><h2>{selected.title}</h2></div><button className="icon-button" onClick={()=>setSelected(null)}><X size={18}/></button></div><p className="task-detail-description">{selected.description}</p><div className="task-detail-fields"><label className="field-label">Status<select value={selected.status} onChange={e=>updateTask(selected.id,{status:e.target.value as TaskStatus})}>{taskColumns.map(column=><option key={column.status}>{column.status}</option>)}</select></label><label className="field-label">Priority<select value={selected.priority} onChange={e=>updateTask(selected.id,{priority:e.target.value as TaskPriority})}><option>Low</option><option>Medium</option><option>High</option><option>Urgent</option></select></label><label className="field-label">Assignee<select value={selected.assignee} onChange={e=>updateTask(selected.id,{assignee:e.target.value})}><option>Unassigned</option>{agents.map(agent=><option key={agent.name}>{agent.name}</option>)}</select></label><label className="field-label">Due date<input value={selected.due} onChange={e=>updateTask(selected.id,{due:e.target.value})}/></label></div><div className="task-detail-dependencies"><strong>Dependencies</strong>{selected.dependencies.length?selected.dependencies.map(dep=><span key={dep}><GitBranch size={12}/>{dep}</span>):<small>No dependencies defined</small>}</div><div className="modal-actions"><button className="secondary-button" onClick={()=>setSelected(null)}>Close</button><button className="primary-button" onClick={()=>{setSelected(null);onNotify("Task changes are saved in this local preview only.");}}>Save changes <Check size={14}/></button></div></div></div>}
  </>;
}

function PriorityBadge({priority}:{priority:TaskPriority}) {
  return <span className={`priority-badge ${priority.toLowerCase()}`}><i/>{priority}</span>;
}


type SharedEntry = { key: string; value: unknown; version: number; hash: string; updatedBy: string; updatedAt: string; intent: string };
type StateRevision = { version: number; agent: string; time: string; intent: string; hash: string; value: unknown };
const initialSharedEntries: SharedEntry[] = [
  { key:"app/config", value:{ environment:"staging", region:"eu-west", featureFlags:{newDashboard:true,betaAuth:false} }, version:8, hash:"sha256:7a9f3c21d8b4…", updatedBy:"agent-backend", updatedAt:"2 min ago", intent:"Align staging runtime configuration with the deployment plan." },
  { key:"spec/auth", value:{ provider:"oauth2", tokenLifetime:3600, refreshRotation:true, scopes:["profile","email","workspace:read"] }, version:6, hash:"sha256:3b82e6a9c104…", updatedBy:"agent-security", updatedAt:"8 min ago", intent:"Document the agreed authentication and authorization contract." },
  { key:"db/schema", value:{ version:3, tables:["users","workspaces","agent_runs"], migrationsPending:1 }, version:5, hash:"sha256:c16d4a80b72f…", updatedBy:"agent-backend", updatedAt:"14 min ago", intent:"Add the agent_runs table to the staging schema." },
  { key:"frontend/theme", value:{ mode:"system", accent:"violet", density:"comfortable" }, version:3, hash:"sha256:91f0d5c44a8e…", updatedBy:"agent-frontend", updatedAt:"21 min ago", intent:"Keep visual preferences consistent across the app shell." },
  { key:"workflow/release", value:{ target:"v0.4.0", status:"in-review", checklist:["tests","security-review","release-notes"] }, version:2, hash:"sha256:2d7e8f11ac03…", updatedBy:"agent-tests", updatedAt:"36 min ago", intent:"Prepare the release checklist for final review." },
  { key:"workspace/description", value:"Shared staging workspace for the Cohort UI implementation.", version:1, hash:"sha256:0a44c2f87e91…", updatedBy:"system", updatedAt:"1 hour ago", intent:"Initial workspace metadata." },
];
const sampleRevisions: Record<string, StateRevision[]> = {
  "app/config":[
    {version:8,agent:"agent-backend",time:"2 min ago",intent:"Align staging runtime configuration with the deployment plan.",hash:"7a9f3c21d8b4",value:{environment:"staging",region:"eu-west",featureFlags:{newDashboard:true,betaAuth:false}}},
    {version:7,agent:"agent-backend",time:"19 min ago",intent:"Enable the new dashboard in staging.",hash:"0b21a4f981c2",value:{environment:"staging",region:"eu-west",featureFlags:{newDashboard:true,betaAuth:false}}},
    {version:6,agent:"agent-frontend",time:"42 min ago",intent:"Add initial feature flag configuration.",hash:"ad41f109a2d0",value:{environment:"staging",region:"eu-west",featureFlags:{newDashboard:false,betaAuth:false}}},
  ],
  "spec/auth":[
    {version:6,agent:"agent-security",time:"8 min ago",intent:"Document the agreed authentication and authorization contract.",hash:"3b82e6a9c104",value:{provider:"oauth2",tokenLifetime:3600,refreshRotation:true,scopes:["profile","email","workspace:read"]}},
    {version:5,agent:"agent-backend",time:"31 min ago",intent:"Add refresh token rotation to the auth contract.",hash:"d4128a6f8b20",value:{provider:"oauth2",tokenLifetime:3600,refreshRotation:true,scopes:["profile","email"]}},
  ],
};
const sampleBranches = [
  {name:"agent-backend/auth-api",agent:"agent-backend",base:"snap_83c1…",changes:2,status:"Ahead of HEAD",tone:"violet"},
  {name:"agent-frontend/app-shell",agent:"agent-frontend",base:"snap_83c1…",changes:1,status:"Ready to commit",tone:"blue"},
  {name:"agent-tests/integration",agent:"agent-tests",base:"snap_91a7…",changes:0,status:"In sync",tone:"green"},
];

function SharedStatePage({onNotify}:{onNotify:(message:string)=>void}) {
  const [entries,setEntries]=useState<SharedEntry[]>(initialSharedEntries);
  const [query,setQuery]=useState("");
  const [namespace,setNamespace]=useState("All namespaces");
  const [selected,setSelected]=useState<SharedEntry|null>(null);
  const [showBranches,setShowBranches]=useState(false);
  const [editing,setEditing]=useState(false);
  const [editValue,setEditValue]=useState("");
  const [creating,setCreating]=useState(false);
  const [newKey,setNewKey]=useState("");
  const [newValue,setNewValue]=useState('{"status":"new"}');
  const namespaces=["All namespaces",...Array.from(new Set(entries.map(entry=>entry.key.split("/")[0])))];
  const filtered=entries.filter(entry=>(namespace==="All namespaces"||entry.key.startsWith(namespace+"/"))&&`${entry.key} ${entry.updatedBy}`.toLowerCase().includes(query.toLowerCase()));
  const current=entries.find(entry=>entry.key===selected?.key)??selected;
  const openEntry=(entry:SharedEntry)=>{setSelected(entry);setEditing(false);setEditValue(JSON.stringify(entry.value,null,2));};
  const saveEdit=()=>{
    if(!selected)return;
    try{const parsed=JSON.parse(editValue);setEntries(items=>items.map(item=>item.key===selected.key?{...item,value:parsed,version:item.version+1,hash:"sha256:preview-"+Math.random().toString(16).slice(2,10),updatedBy:"you",updatedAt:"Just now",intent:"Edited in the local interface preview."}:item));setSelected(item=>item?{...item,value:parsed,version:item.version+1,updatedBy:"you",updatedAt:"Just now",intent:"Edited in the local interface preview."}:item);setEditing(false);onNotify("Value updated in local preview only. No workspace commit was created.");}catch{onNotify("Invalid JSON. Correct the value before saving.");}
  };
  const createEntry=()=>{
    if(!newKey.includes("/")||entries.some(item=>item.key===newKey.trim())){onNotify("Use a unique key with a namespace, for example app/config.");return;}
    try{const value=JSON.parse(newValue);const entry:SharedEntry={key:newKey.trim(),value,version:1,hash:"sha256:preview-"+Math.random().toString(16).slice(2,10),updatedBy:"you",updatedAt:"Just now",intent:"Created in the local interface preview."};setEntries(items=>[entry,...items]);setCreating(false);setNewKey("");onNotify("Key added to local preview only. It is not committed to the workspace.");}catch{onNotify("Value must be valid JSON.");}
  };
  return <>
    <section className="state-hero">
      <div className="state-hero-main"><div className="state-hero-icon"><Database size={20}/></div><div><div className="state-eyebrow">WORKSPACE SNAPSHOT <span className="snapshot-live-dot"/> CURRENT HEAD</div><h2>Shared state</h2><p>A versioned, content-addressed view of the data agents are coordinating around.</p></div></div>
      <div className="snapshot-id"><span>HEAD VERSION</span><strong>snap_9f2a7c81d4e6</strong><small><GitCommit size={12}/> 3 parent snapshots</small></div>
    </section>
    <section className="state-stats">
      <div><span>Keys in HEAD</span><strong>{String(entries.length).padStart(2,"0")}</strong><small>Current snapshot entries</small></div>
      <div><span>Active branches</span><strong>03</strong><small>Isolated agent workspaces</small></div>
      <div><span>Recent revisions</span><strong>12</strong><small>Across the sample history</small></div>
      <div><span>Content integrity</span><strong className="metric-green">Verified</strong><small>Hash-addressed values</small></div>
    </section>
    <section className="panel state-entries-panel">
      <div className="state-panel-heading"><div><h2>Snapshot entries <span className="count-chip">{filtered.length}</span></h2><p>Each key points to a value in the current immutable snapshot.</p></div><button className="primary-button" onClick={()=>setCreating(true)}><Plus size={14}/> Add key</button></div>
      <div className="state-controls"><label className="registry-search"><Search size={15}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search keys or agents..."/></label><div className="filter-control"><Filter size={14}/><select value={namespace} onChange={e=>setNamespace(e.target.value)}>{namespaces.map(item=><option key={item}>{item}</option>)}</select><ChevronDown size={13}/></div><button className="icon-button refresh-button" onClick={()=>onNotify("Snapshot refreshed from sample data. Runtime connection is not active.")} aria-label="Refresh snapshot"><RefreshCw size={15}/></button></div>
      <div className="state-table-wrap"><div className="state-table-head"><span>KEY</span><span>VERSION</span><span>LAST WRITER</span><span>UPDATED</span><span>CONTENT HASH</span><span/></div>
        {filtered.map(entry=><button className="state-row" key={entry.key} onClick={()=>openEntry(entry)}>
          <div className="state-key-cell"><span className="state-key-icon"><FileJson size={15}/></span><div><strong>{entry.key}</strong><small>{entry.key.split("/")[0]} namespace</small></div></div>
          <span className="state-version">v{entry.version}</span><span className="state-writer">{entry.updatedBy}</span><span className="state-updated"><Clock3 size={12}/>{entry.updatedAt}</span><span className="state-hash">{entry.hash}</span><ChevronRight size={15} className="registry-chevron"/>
        </button>)}
        {filtered.length===0&&<div className="registry-empty"><Search size={20}/><strong>No keys found</strong><span>Try another key or namespace.</span></div>}
      </div>
      <div className="state-table-footer"><span>Showing {filtered.length} of {entries.length} keys</span><span>Sample data · not connected to runtime</span></div>
    </section>
    <section className="state-lower-grid">
      <div className="panel branch-panel"><div className="state-panel-heading"><div><h2>Agent branches</h2><p>Isolated working copies based on a snapshot.</p></div><button className="text-button" onClick={()=>setShowBranches(value=>!value)}>{showBranches?"Hide":"View all"} <ArrowRight size={13}/></button></div>
        {sampleBranches.slice(0,showBranches?3:2).map(item=><div className="branch-state-row" key={item.name}><span className={`branch-state-icon ${item.tone}`}><GitBranch size={15}/></span><div className="branch-state-info"><strong>{item.name}</strong><small>{item.agent} · base {item.base}</small></div><div className="branch-state-meta"><strong>{item.changes} changes</strong><span className={`branch-status ${item.tone}`}>{item.status}</span></div></div>)}
        <div className="branch-panel-foot"><GitBranch size={13}/> Branches stay isolated until a successful commit.</div>
      </div>
      <div className="panel integrity-panel"><div className="integrity-heading"><div className="integrity-icon"><Hash size={17}/></div><div><h2>Content-addressed storage</h2><p>Values are canonicalized and hashed.</p></div></div><div className="integrity-flow"><div><span>JSON value</span><strong>Canonicalize</strong></div><ArrowRight size={14}/><div><span>SHA-256</span><strong>Content hash</strong></div></div><p className="integrity-note">Snapshot IDs include the entry hashes and parent snapshot history. Identical content produces the same content hash.</p><button className="text-button" onClick={()=>onNotify("Hash verification details will be available when the runtime is connected.")}>Explore integrity details <ArrowRight size={13}/></button></div>
    </section>
    {current&&<div className="modal-backdrop" onClick={()=>setSelected(null)}><div className="state-detail-modal" onClick={e=>e.stopPropagation()}>
      <div className="modal-head"><div><span className="eyebrow">SNAPSHOT ENTRY · {current.key.split("/")[0].toUpperCase()}</span><h2>{current.key}</h2></div><button className="icon-button" onClick={()=>setSelected(null)}><X size={18}/></button></div>
      <div className="state-detail-meta"><span>Version <strong>v{current.version}</strong></span><span>Last writer <strong>{current.updatedBy}</strong></span><span>Updated <strong>{current.updatedAt}</strong></span></div>
      <div className="state-value-heading"><strong>Current value</strong><span><Hash size={11}/>{current.hash}</span></div>
      {editing?<textarea className="state-json-editor" value={editValue} onChange={e=>setEditValue(e.target.value)} spellCheck={false}/>:<pre className="state-json-view">{JSON.stringify(current.value,null,2)}</pre>}
      <div className="state-intent"><span>WRITE INTENT</span><p>{current.intent||"No intent recorded for this key."}</p></div>
      <div className="state-history"><div className="state-history-head"><strong><History size={14}/> Revision history</strong><span>{(sampleRevisions[current.key]??[{version:current.version,agent:current.updatedBy,time:current.updatedAt,intent:current.intent,hash:current.hash,value:current.value}]).length} revisions shown</span></div>
        {(sampleRevisions[current.key]??[{version:current.version,agent:current.updatedBy,time:current.updatedAt,intent:current.intent,hash:current.hash,value:current.value}]).map(rev=><div className="revision-row" key={rev.version}><span className="revision-marker"/><div><strong>v{rev.version} · {rev.agent}</strong><small>{rev.intent}</small></div><span>{rev.time}</span></div>)}
      </div>
      <div className="modal-actions"><button className="secondary-button" onClick={()=>{setEditing(v=>!v);setEditValue(JSON.stringify(current.value,null,2));}}>{editing?"Cancel edit":<><Pencil size={13}/> Edit value</>}</button>{editing&&<button className="primary-button" onClick={saveEdit}><Save size={13}/> Save preview</button>}</div>
    </div></div>}
    {creating&&<div className="modal-backdrop" onClick={()=>setCreating(false)}><div className="task-modal state-create-modal" onClick={e=>e.stopPropagation()}><div className="modal-head"><div><span className="eyebrow">WORKSPACE SNAPSHOT</span><h2>Add a state key</h2></div><button className="icon-button" onClick={()=>setCreating(false)}><X size={18}/></button></div><p className="modal-copy">Create a namespaced key in this local preview. A real write requires an agent branch and a successful workspace commit.</p><label className="field-label">Key<input value={newKey} onChange={e=>setNewKey(e.target.value)} placeholder="e.g. app/config"/></label><label className="field-label">JSON value<textarea className="state-json-editor create-json" value={newValue} onChange={e=>setNewValue(e.target.value)} spellCheck={false}/></label><div className="modal-actions"><button className="secondary-button" onClick={()=>setCreating(false)}>Cancel</button><button className="primary-button" onClick={createEntry}>Add key <ArrowRight size={14}/></button></div></div></div>}
  </>;
}


type NotifyProps={onNotify:(message:string)=>void};
const branchesSeed=[{name:"draft-api",agent:"agent-backend",base:"7f3a91",files:12,status:"Ready"},{name:"app-shell",agent:"agent-frontend",base:"7f3a91",files:9,status:"Conflict"},{name:"it-suite",agent:"agent-tests",base:"b20d4e",files:6,status:"Ready"},{name:"staging-db",agent:"agent-database",base:"b20d4e",files:7,status:"Ready"},{name:"authz-review",agent:"agent-security",base:"01ff3c",files:4,status:"Conflict"}];
function BranchesPage({onNotify}:NotifyProps){const [rows,setRows]=useState(branchesSeed);const [filter,setFilter]=useState("All");const [q,setQ]=useState("");const data=rows.filter(x=>(filter==="All"||x.status===filter)&&(x.name+x.agent).toLowerCase().includes(q.toLowerCase()));return <><CoordBanner title="Branch workspace" text="Agents work in isolated branches. Changes reach the shared head only after validation and a successful merge."/><CoordStats items={[["Open branches",String(rows.length)],["Ready to merge",String(rows.filter(x=>x.status==="Ready").length)],["Conflicts",String(rows.filter(x=>x.status==="Conflict").length)],["Merged",String(rows.filter(x=>x.status==="Merged").length)]]}/><section className="panel coord-panel"><div className="coord-toolbar"><div><h2>Agent branches</h2><p>Branch owner, base snapshot and merge readiness.</p></div><span className="sample-data-label"><i/> SAMPLE DATA</span></div><div className="coord-controls"><label className="registry-search"><Search size={14}/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search branch or agent"/></label><select className="coord-select" value={filter} onChange={e=>setFilter(e.target.value)}><option value="All">All branches</option><option>Ready</option><option>Conflict</option></select></div><div className="coord-table"><div className="coord-table-head branch-cols"><span>BRANCH</span><span>BASE</span><span>CHANGES</span><span>STATUS</span><span>ACTION</span></div>{data.map(b=><div className="coord-row branch-cols" key={b.name}><div><strong className="mono-value">{b.name}</strong><small>{b.agent}</small></div><span className="mono-value">{b.base}…</span><span>{b.files} files</span><span className={"coord-status "+(b.status==="Ready"?"good":b.status==="Conflict"?"warn":"neutral")}><i/>{b.status}</span><span>{b.status==="Ready"?<button className="btn-small" onClick={()=>{setRows(v=>v.map(x=>x.name===b.name?{...x,status:"Merged"}:x));onNotify("Preview merge only. No runtime commit was created.");}}>Merge</button>:b.status==="Conflict"?<button className="btn-small" onClick={()=>onNotify("Inspect this branch in the Conflicts view.")}>Review</button>:<span>—</span>}</span></div>)}</div><div className="coord-foot">Branch actions are local preview state. No runtime is connected.</div></section></>}
type Lease={key:string;owner:string;seconds:number;fence:number;branch:string;status:string};
const leaseSeed:Lease[]=[{key:"shared/api-schema",owner:"agent-backend",seconds:48,fence:104,branch:"draft-api",status:"Active"},{key:"shared/users",owner:"agent-database",seconds:0,fence:87,branch:"staging-db",status:"Expired"},{key:"src/routes.ts",owner:"agent-frontend",seconds:126,fence:112,branch:"app-shell",status:"Active"},{key:"spec/auth",owner:"agent-security",seconds:19,fence:115,branch:"authz-review",status:"Active"},{key:"test-results",owner:"agent-tests",seconds:0,fence:92,branch:"it-suite",status:"Waiting"}];
function LeasesPage({onNotify}:NotifyProps){const [rows,setRows]=useState(leaseSeed);const [required,setRequired]=useState(true);const act=(key:string,kind:string)=>{setRows(v=>v.map(x=>x.key===key?{...x,seconds:kind==="Release"?0:60,fence:kind==="Release"?x.fence:x.fence+1,status:kind==="Release"?"Expired":"Active"}:x));onNotify(kind+" simulated locally. Runtime state is unchanged.");};return <><CoordBanner title="Lease manager" text="Time-bound ownership prevents concurrent writes. Fencing tokens reject stale owners after a lease changes hands."/><CoordStats items={[["Active leases",String(rows.filter(x=>x.status==="Active").length)],["Expiring ≤ 30s",String(rows.filter(x=>x.status==="Active"&&x.seconds<=30).length)],["Expired",String(rows.filter(x=>x.status==="Expired").length)],["Waiting",String(rows.filter(x=>x.status==="Waiting").length)]]}/><section className="panel coord-panel"><div className="coord-toolbar"><div><h2>Resource ownership</h2><p>Owner, expiry and monotonically increasing fencing token.</p></div><span className="sample-data-label"><i/> SAMPLE DATA</span></div><div className="coord-table"><div className="coord-table-head lease-cols"><span>RESOURCE</span><span>OWNER</span><span>LEASE</span><span>FENCE</span><span>ACTIONS</span></div>{rows.map(l=><div className="coord-row lease-cols" key={l.key}><div><strong className="mono-value">{l.key}</strong><small>{l.branch}</small></div><span>{l.owner}</span><span><b className={l.seconds>0&&l.seconds<=30?"metric-amber":""}>{l.seconds?l.seconds+" sec":"—"}</b><small>{l.status}</small></span><span className="mono-value">#{l.fence}</span><span className="row-actions">{l.status==="Active"?<><button className="btn-small" onClick={()=>act(l.key,"Renew")}>Renew</button><button className="btn-small subtle" onClick={()=>act(l.key,"Release")}>Release</button></>:<button className="btn-small" onClick={()=>act(l.key,"Acquire")}>Acquire</button>}</span></div>)}</div><div className="lease-policy"><div><strong>Require leases for writes</strong><p>Reject writes without valid ownership and the current fencing token.</p></div><button className={"toggle-switch "+(required?"on":"")} onClick={()=>setRequired(v=>!v)}/></div><div className="coord-foot">Illustrative lease data · local interactions only</div></section><section className="lease-explainer"><strong><Hash size={16}/> Why fencing tokens matter</strong><p>A lease may expire while an agent is paused. When another agent acquires the resource, the token increases. Storage must reject writes carrying an older token—even if the previous owner wakes up.</p></section></>}
const conflictSeed=[{key:"src/routes.ts",agent:"agent-frontend",branch:"app-shell",base:"routes = [home]",head:"routes = [home, users]",incoming:"routes = [home, settings]",reason:"Both agents changed the route registry from the same base snapshot."},{key:"spec/auth",agent:"agent-security",branch:"authz-review",base:"scopes = [profile]",head:"scopes = [profile, email]",incoming:"scopes = [profile, workspace:read]",reason:"Concurrent authorization scope updates need an explicit decision."}];
function ConflictsPage({onNotify}:NotifyProps){const [rows,setRows]=useState(conflictSeed);const [idx,setIdx]=useState(0);const [strategy,setStrategy]=useState("PreferHead");const [reason,setReason]=useState("");const [history,setHistory]=useState<string[]>([]);const item=rows[idx];const resolve=()=>{if(!item)return;if(!reason.trim()){onNotify("A rationale is required before recording the decision.");return;}setHistory(v=>[item.key+" · "+strategy+" · "+reason,...v]);setRows(v=>v.filter(x=>x.key!==item.key));setIdx(0);setReason("");onNotify("Resolution recorded in this preview only.");};return <><CoordBanner title="Conflict review" text="Compare the common base, current workspace head and incoming branch before recording a resolution."/><div className="conflict-layout"><section className="panel conflict-list"><h2>Needs resolution <span className="count-chip">{rows.length}</span></h2>{rows.map((x,i)=><button className={"conflict-item "+(idx===i?"selected":"")} key={x.key} onClick={()=>setIdx(i)}><AlertTriangle size={15}/><span><b className="mono-value">{x.key}</b><small>{x.agent} · {x.branch}</small></span><ChevronRight size={14}/></button>)}{!rows.length&&<p className="muted-text">No unresolved conflicts.</p>}</section><section className="panel conflict-detail">{item?<><h2>{item.key}</h2><p>{item.reason}</p><div className="three-way">{[["BASE",item.base],["HEAD",item.head],["INCOMING",item.incoming]].map(([label,value])=><div key={label}><span>{label}</span><pre>{value}</pre></div>)}</div><b>Resolution strategy</b><div className="strategy-options">{["PreferHead","PreferBranch","PreferAgent"].map(x=><label key={x}><input type="radio" name="resolve" checked={strategy===x} onChange={()=>setStrategy(x)}/>{x}</label>)}</div><label className="field-label">Decision rationale<textarea rows={3} value={reason} onChange={e=>setReason(e.target.value)} placeholder="Why should this version win?"/></label><button className="primary-button" onClick={resolve}>Record decision <Check size={14}/></button></>:<h2>All conflicts resolved</h2>}{history.length>0&&<div className="decision-history"><b>Recorded decisions</b>{history.map(x=><p key={x}>{x}</p>)}</div>}</section></div></>}
const eventSeed=[{id:"evt_0192",time:"10:42:18",agent:"system",action:"workspace.snapshot.created",detail:"Snapshot 7f3a91 created",payload:'{"snapshot":"7f3a91","keys":12}'},{id:"evt_0191",time:"10:41:52",agent:"agent-backend",action:"lease.acquired",detail:"Acquired shared/api-schema · fence #104",payload:'{"key":"shared/api-schema","ttl":60,"fence":104}'},{id:"evt_0190",time:"10:40:33",agent:"agent-frontend",action:"commit.conflict",detail:"Conflict on src/routes.ts",payload:'{"branch":"app-shell","key":"src/routes.ts"}'},{id:"evt_0189",time:"10:39:07",agent:"agent-tests",action:"commit.accepted",detail:"Committed test-results to branch it-suite",payload:'{"key":"test-results","version":14}'},{id:"evt_0188",time:"10:37:21",agent:"agent-database",action:"lease.released",detail:"Released shared/users",payload:'{"key":"shared/users","fence":87}'}];
function EventLogPage(){const [q,setQ]=useState("");const [selected,setSelected]=useState(eventSeed[0]);const rows=eventSeed.filter(x=>(x.action+x.agent+x.detail).toLowerCase().includes(q.toLowerCase()));return <><CoordBanner title="Event stream" text="An ordered record of branch operations, lease transitions, state commits and conflict decisions."/><section className="panel coord-panel"><div className="coord-toolbar"><div><h2>Workspace events</h2><p>Inspect actor, action and structured payload.</p></div><span className="sample-data-label"><i/> SAMPLE DATA</span></div><label className="registry-search event-search"><Search size={14}/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search events"/></label><div className="event-layout"><div className="event-list">{rows.map(e=><button className={"event-row "+(selected.id===e.id?"selected":"")} key={e.id} onClick={()=>setSelected(e)}><span className="event-marker"/><span><b>{e.action}</b><small>{e.agent} · {e.detail}</small></span><time>{e.time}</time></button>)}</div><aside className="event-inspector"><span className="eyebrow">EVENT PAYLOAD</span><h3>{selected.id}</h3><p>{selected.agent} · {selected.time}</p><pre>{JSON.stringify(JSON.parse(selected.payload),null,2)}</pre><small>Sample event · integrity not verified</small></aside></div></section></>}
function McpPage({onNotify}:NotifyProps){const [transport,setTransport]=useState("stdio");const toolsList=["cohort_list_agents","cohort_create_branch","cohort_read_state","cohort_write_state","cohort_commit","cohort_acquire_lease","cohort_release_lease","cohort_read_events","cohort_resolve_conflict"];const config=transport==="stdio"?'{"mcpServers":{"cerbere-cohort":{"command":"cohort-mcp","args":["serve"]}}}':'{"mcpServers":{"cerbere-cohort":{"url":"http://localhost:7331/mcp"}}}';return <><CoordBanner title="MCP integration" text="Expose coordination primitives as tools compatible agents can call during execution."/><div className="mcp-grid"><section className="panel settings-card"><h2>Client configuration</h2><p>Example local client configuration. The server is not running from this dashboard.</p><div className="strategy-options">{["stdio","http"].map(x=><label key={x}><input type="radio" checked={transport===x} onChange={()=>setTransport(x)}/>{x.toUpperCase()}</label>)}</div><pre className="mcp-code">{config}</pre><button className="primary-button" onClick={()=>{navigator.clipboard?.writeText(config);onNotify("Configuration copied if clipboard access is permitted.");}}><FileJson size={14}/> Copy config</button></section><section className="panel settings-card"><h2>Tool surface <span className="count-chip">{toolsList.length}</span></h2>{toolsList.map((x,i)=><div className="mcp-tool" key={x}><span>{String(i+1).padStart(2,"0")}</span><code>{x}</code><small>Runtime tool</small></div>)}</section></div><section className="lease-explainer"><strong><Network size={16}/> Coordination, not agent generation</strong><p>Cohort is the shared coordination layer: isolated branches, versioned shared state, leases, conflict handling and auditable events. Agents can be built with different frameworks.</p></section></>}
function SettingsPage({onNotify}:NotifyProps){const [name,setName]=useState("Personal workspace");const [lease,setLease]=useState(true);const [audit,setAudit]=useState(true);const [policy,setPolicy]=useState("Require explicit decision");return <><CoordBanner title="Workspace settings" text="Configure coordination policies and workspace metadata. Controls are preview-only until runtime integration."/><div className="settings-layout"><section className="panel settings-card"><h2>Workspace profile</h2><label className="field-label">Workspace name<input value={name} onChange={e=>setName(e.target.value)}/></label><div className="settings-readonly"><span>Workspace ID</span><code>ws_demo_7f3a91</code></div><div className="settings-readonly"><span>Storage</span><code>SQLite · local</code></div><button className="primary-button" onClick={()=>onNotify("Workspace settings updated in preview only.")}><Save size={14}/> Save</button></section><section className="panel settings-card"><h2>Coordination policies</h2><SettingToggle title="Require leases for writes" desc="Reject writes without current ownership and fencing token." value={lease} onChange={setLease}/><SettingToggle title="Append-only event history" desc="Preserve ordered coordination event records." value={audit} onChange={setAudit}/><label className="field-label">Conflict policy<select value={policy} onChange={e=>setPolicy(e.target.value)}><option>Require explicit decision</option><option>Prefer current head</option><option>Prefer incoming branch</option></select></label><button className="primary-button" onClick={()=>onNotify("Policies saved in preview only; runtime configuration is unchanged.")}><Save size={14}/> Save policies</button></section></div></>}
function SettingToggle({title,desc,value,onChange}:{title:string;desc:string;value:boolean;onChange:(v:boolean)=>void}){return <div className="setting-row"><div><b>{title}</b><p>{desc}</p></div><button className={"toggle-switch "+(value?"on":"")} onClick={()=>onChange(!value)}/></div>}
function CoordBanner({title,text}:{title:string;text:string}){return <section className="coord-summary"><div><strong>{title}</strong><p>{text}</p></div><span className="sample-data-label"><i/> SAMPLE DATA</span></section>}
function CoordStats({items}:{items:string[][]}){return <section className="coord-metrics">{items.map(([label,value])=><div key={label}><span>{label}</span><b>{value}</b></div>)}</section>}
export default App;