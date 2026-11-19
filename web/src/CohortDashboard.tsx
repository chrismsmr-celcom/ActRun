import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, ChevronDown, Command, Database, GitBranch, LayoutDashboard, Moon, PanelLeftClose, PanelLeftOpen, RefreshCw, ScrollText, Settings2, Sun } from "lucide-react";
import cohortLogo from "./cohortLogo";
import "./cohort-dashboard.css";

type Tab = "Overview" | "Branches" | "State" | "Event log" | "Settings";
type EventItem = { event_id: string; timestamp: string; agent_id: string; action: string; payload: Record<string, unknown>; schema_version: string };
type Branch = { id: string; name: string; agent_id: string; base_version: string; status: string; conflicting_keys: string[]; created_at: string };
type StateItem = { key: string; value_hash: string; value: unknown };
type Lease = { key: string; agent_id: string; expires_at: number; acquired_at: number; fencing_token: number };
type Overview = { head: string; key_count: number; snapshot_count: number; event_count: number; active_lease_count: number; commit_count: number; conflict_count: number; branches: number; sample_data: boolean };
type Settings = { require_leases: boolean; persistence: string; database_path: string; multi_process: boolean; authentication: boolean };
type ConflictDetail = { key: string; base: unknown; head: unknown; branch: unknown; base_present: boolean; head_present: boolean; branch_present: boolean };

const API = (import.meta as any).env?.VITE_API_URL || "";
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body?.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.message || JSON.stringify(detail || body));
  }
  return body as T;
}
const short = (value?: string) => value ? value.slice(0, 7) + "…" + value.slice(-4) : "—";
const timeAgo = (value: string) => {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
};
const dateTime = (seconds: number) => new Date(seconds * 1000).toLocaleTimeString();

export default function CohortDashboard() {
  const [tab, setTab] = useState<Tab>("Overview");
  const [sub, setSub] = useState<"Coordination" | "Conflicts">("Coordination");
  const [dark, setDark] = useState(() => localStorage.getItem("cohort-theme") === "dark");
  const [banner, setBanner] = useState(true);
  const [sidebar, setSidebar] = useState(false);
  const [navCollapsed, setNavCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [state, setState] = useState<{ head: string; parent: string | null; items: StateItem[] }>({ head: "", parent: null, items: [] });
  const [leases, setLeases] = useState<Lease[]>([]);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [filter, setFilter] = useState("");
  const [branchStatus, setBranchStatus] = useState<"open" | "merged">("open");
  const [selected, setSelected] = useState<string[]>([]);
  const [conflictDetails, setConflictDetails] = useState<ConflictDetail[]>([]);
  const [replayIndex, setReplayIndex] = useState(0);
  const [resolveBranch, setResolveBranch] = useState<Branch | null>(null);
  const [strategy, setStrategy] = useState("PreferHead");
  const [rationale, setRationale] = useState("");
  const [agentPriority, setAgentPriority] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [agentId, setAgentId] = useState("agent-new");
  const [branchName, setBranchName] = useState("");
  const [leaseAgent, setLeaseAgent] = useState("operator");
  const [leaseKey, setLeaseKey] = useState("");
  const [trace, setTrace] = useState<{ actions: Record<string, number>; bad: number } | null>(null);
  const [traceText, setTraceText] = useState("");
  const [deadlock, setDeadlock] = useState(false);

  const notify = (message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 3000);
  };
  const refresh = useCallback(async () => {
    try {
      const [o, b, s, e, l, cfg] = await Promise.all([
        api<Overview>("/overview"), api<{ items: Branch[] }>("/branches"),
        api<typeof state>("/state"), api<{ items: EventItem[] }>("/events?limit=300"),
        api<{ items: Lease[] }>("/leases"), api<Settings>("/settings"),
      ]);
      setOverview(o); setBranches(b.items); setState(s); setEvents(e.items);
      setLeases(l.items); setSettings(cfg); setConnected(true); setError("");
      
      setReplayIndex((current) => Math.min(current, Math.max(0, e.items.length - 1)));
    } catch (err) {
      setConnected(false); setError(err instanceof Error ? err.message : "Unable to reach Cohort API");
    }
  }, []);
  useEffect(() => { void refresh(); const id = window.setInterval(() => void refresh(), 5000); return () => window.clearInterval(id); }, [refresh]);
  useEffect(() => { document.documentElement.dataset.theme = dark ? "dark" : "light"; localStorage.setItem("cohort-theme", dark ? "dark" : "light"); }, [dark]);

  const run = async (action: () => Promise<unknown>, message: string) => {
    setBusy(true);
    try { await action(); await refresh(); notify(message); }
    catch (err) { notify(err instanceof Error ? err.message : "Action failed"); }
    finally { setBusy(false); }
  };
  const openBranches = branches.filter((b) => b.status === "open");
  const visibleBranches = branches.filter((b) => (branchStatus === "open" ? b.status === "open" : b.status === "merged") &&
    (b.name + " " + b.agent_id).toLowerCase().includes(filter.toLowerCase()));
  const conflicts = branches.filter((b) => b.status === "open" && b.conflicting_keys.length > 0);
  const actionCounts = useMemo(() => {
    const days = Array.from({ length: 14 }, (_, i) => {
      const date = new Date(); date.setDate(date.getDate() - (13 - i)); date.setHours(0, 0, 0, 0);
      return { label: date.getDate().toString(), date: date.toDateString(), commits: 0, conflicts: 0 };
    });
    events.forEach((event) => {
      const day = days.find((d) => d.date === new Date(event.timestamp).toDateString());
      if (!day) return;
      if (/commit|resolved/.test(event.action) && !/conflict|abort/.test(event.action)) day.commits++;
      if (/conflict/.test(event.action)) day.conflicts++;
    });
    return days;
  }, [events]);

  const openResolve = async (branch: Branch) => {
    setResolveBranch(branch);
    setConflictDetails([]);
    try {
      const detail = await api<{ conflicts: ConflictDetail[] }>(`/branches/${branch.id}/conflict`);
      setConflictDetails(detail.conflicts);
    } catch (err) {
      notify(err instanceof Error ? err.message : "Could not load conflict details");
    }
  };
  const createBranch = async () => {
    if (!branchName.trim() || !agentId.trim()) return;
    await run(async () => {
      await api<Branch>("/branches", { method: "POST", body: JSON.stringify({ agent_id: agentId.trim(), name: branchName.trim() }) });
      setCreateOpen(false); setBranchName("");
    }, "Branch created");
  };
  const mergeBranch = (branch: Branch) => run(async () => {
    const result = await api<any>(`/branches/${branch.id}/commit`, { method: "POST" });
    if (result.conflict) throw new Error(`Merge blocked. Conflicting keys: ${result.conflicting_keys.join(", ")}`);
  }, "Branch merged");
  const resolve = async () => {
    if (!resolveBranch || !rationale.trim()) return;
    await run(async () => {
      await api(`/branches/${resolveBranch.id}/resolve`, { method: "POST", body: JSON.stringify({ strategy, rationale, priority: agentPriority.split(",").map((x) => x.trim()).filter(Boolean) }) });
      setResolveBranch(null); setRationale(""); setAgentPriority("");
    }, "Resolution recorded and branch committed");
  };
  const acquireLease = () => {
    if (!leaseKey.trim() || !leaseAgent.trim()) return;
    void run(async () => { await api("/leases", { method: "POST", body: JSON.stringify({ agent_id: leaseAgent, key: leaseKey, duration_seconds: 60 }) }); setLeaseKey(""); }, "Lease acquired");
  };
  const releaseLease = (lease: Lease) => run(async () => {
    await api(`/leases/${encodeURIComponent(lease.key)}?agent_id=${encodeURIComponent(lease.agent_id)}`, { method: "DELETE" });
  }, "Lease released");
  const parseTrace = (text: string) => {
    const actions: Record<string, number> = {}; let bad = 0;
    text.split(/\r?\n/).filter((line) => line.trim()).forEach((line) => {
      try { const action = JSON.parse(line).action || "unknown"; actions[action] = (actions[action] || 0) + 1; }
      catch { bad++; }
    });
    setTrace({ actions, bad });
  };
  const replayEvent = events[replayIndex] || null;

  return <div className={`cohort-app${navCollapsed ? " nav-collapsed" : ""}${mobileNavOpen ? " mobile-nav-open" : ""}`}>
    <aside className="app-nav">
      <div className="brand-lockup">
        <img className="brand-logo" src={cohortLogo} alt="Cohort" />
        <div className="brand-wordmark"><strong>cohort</strong><small>BY CERBERE</small></div>
        <button className="nav-collapse-button" onClick={()=>{if(window.matchMedia("(max-width: 720px)").matches)setMobileNavOpen(!mobileNavOpen);else setNavCollapsed(!navCollapsed)}} title={navCollapsed ? "Expand navigation" : "Collapse navigation"} aria-label={navCollapsed ? "Expand navigation" : "Collapse navigation"}>{navCollapsed?<PanelLeftOpen size={16}/>:<PanelLeftClose size={16}/>}</button>
      </div>
      <div className="workspace-picker">
        <div className="workspace-avatar">W</div>
        <div className="workspace-meta"><strong>Workspace</strong><small>main environment</small></div>
        <ChevronDown className="nav-chevron" size={15}/>
      </div>
      <div className="nav-section-label">WORKSPACE</div>
      <nav className="primary-nav">
        {([
          {item:"Overview" as Tab, icon:<LayoutDashboard size={17}/>, label:"Overview"},
          {item:"Branches" as Tab, icon:<GitBranch size={17}/>, label:"Branches"},
          {item:"State" as Tab, icon:<Database size={17}/>, label:"Shared state"},
          {item:"Event log" as Tab, icon:<ScrollText size={17}/>, label:"Event log"},
          {item:"Settings" as Tab, icon:<Settings2 size={17}/>, label:"Settings"}
        ]).map(({item,icon,label}) => <button key={item} className={tab===item?"nav-link active":"nav-link"} onClick={()=>{setTab(item);setMobileNavOpen(false)}} title={navCollapsed?label:undefined}><span className="nav-icon">{icon}</span><span className="nav-label">{label}</span>{item==="Branches"&&openBranches.length>0&&<small>{openBranches.length}</small>}</button>)}
      </nav>
      <div className="nav-bottom">
        <div className="runtime-status-card">
          <div className="runtime-status-heading"><i className={connected?"is-online":""}/><strong>Runtime status</strong></div>
          <p>{connected?"Connected to Cohort API":"Waiting for runtime connection"}</p>
          <button onClick={()=>void refresh()}>{connected?"Refresh status":"Retry connection"} <span>↗</span></button>
        </div>
        <button className="profile-control"><div className="profile-avatar">C</div><span><strong>Workspace admin</strong><small>Administrator</small></span><b>···</b></button>
      </div>
    </aside>
    {mobileNavOpen&&<button className="mobile-nav-backdrop" aria-label="Close navigation" onClick={()=>setMobileNavOpen(false)}/>}

    <div className="app-main">
      <header className="topbar">
        <div className="breadcrumbs"><button className="topbar-icon mobile-nav-trigger" onClick={()=>setMobileNavOpen(!mobileNavOpen)} title="Open navigation"><PanelLeftOpen size={16}/></button><span>Workspace</span><b>/</b><strong>{tab==="State"?"Shared state":tab}</strong></div>
        <div className="topbar-actions">
          <span className={connected?"connection-pill connected":"connection-pill"}><i/>{connected?"Runtime connected":"Runtime offline"}</span>
          <button className="topbar-icon" onClick={()=>void refresh()} title="Refresh data"><RefreshCw size={15}/></button>
          <button className="topbar-icon" onClick={()=>setDark(!dark)} title="Toggle theme">{dark?<Sun size={16}/>:<Moon size={16}/>}</button>
          <button className="topbar-icon" onClick={()=>setSidebar(!sidebar)} title="Technical inspector"><Command size={16}/></button>
        </div>
      </header>

      <main className="page-content">
        {error&&<div className="api-error"><strong>Runtime unavailable</strong><span>{error}</span><button onClick={()=>void refresh()}>Retry</button></div>}

        {tab==="Overview"&&<>
          <div className="page-heading">
            <div><div className="eyebrow">WORKSPACE / MAIN</div><h1>Workspace overview</h1><p>See how your agents coordinate, share state and resolve competing changes.</p></div>
            <div className="heading-actions"><span className="updated-label">Updated just now</span><button className="button-primary" onClick={()=>setCreateOpen(true)}><span className="button-icon"><Activity size={14}/></span> New branch</button></div>
          </div>
          <div className="health-strip">
            <div className="health-copy"><span className="health-indicator"/><div><strong>{connected?"Coordination runtime is reachable":"Runtime connection required"}</strong><small>{connected?"Workspace data is being read from the live API.":"Start the Cohort API to load live workspace activity."}</small></div></div>
            <div className="health-meta"><span>HEAD <code>{short(state.head)}</code></span><span>{state.items.length} shared keys</span><span>{overview?.snapshot_count??0} snapshots</span></div>
          </div>
          <section className="metric-grid">
            <Metric label="Open branches" value={openBranches.length}/>
            <Metric label="Unresolved conflicts" value={conflicts.length} tone={conflicts.length?"red":""}/>
            <Metric label="Active leases" value={leases.length}/>
            <Metric label="Recorded events" value={overview?.event_count??events.length}/>
          </section>
          <div className="overview-grid">
            <section className="surface-card activity-card">
              <div className="surface-heading"><div><h2>Coordination activity</h2><p>Commits and conflict events · last 14 days</p></div><span className="subtle-tag">LIVE DATA</span></div>
              <div className="chart-legend"><span><i className="legend-commit"/>Commits</span><span><i className="legend-conflict"/>Conflicts</span></div>
              <div className="activity-chart">
                <div className="chart-axis"><span>{Math.max(1,...actionCounts.map(d=>Math.max(d.commits,d.conflicts)))}</span><span>0</span></div>
                <div className="chart-columns">{actionCounts.map((d,i)=>{const max=Math.max(1,...actionCounts.map(x=>Math.max(x.commits,x.conflicts)));return <div className="chart-day" key={i}><div className="chart-bars"><i className="commit-bar" style={{height:(d.commits/max*100)+"%"}} title={d.commits+" commits"}/><i className="conflict-bar" style={{height:(d.conflicts/max*100)+"%"}} title={d.conflicts+" conflicts"}/></div><small>{i%2===0?d.label:""}</small></div>})}</div>
              </div>
              <div className="chart-footer"><span>Daily event volume</span><span>{events.length} events loaded</span></div>
            </section>
            <section className="surface-card conflict-card">
              <div className="surface-heading"><div><h2>Needs attention</h2><p>Conflicts that require a resolution</p></div><span className={conflicts.length?"count-badge warning":"count-badge"}>{conflicts.length}</span></div>
              {conflicts.length?conflicts.slice(0,4).map(branch=><div className="attention-row" key={branch.id}><div className="attention-mark">!</div><div className="attention-detail"><strong>{branch.name}</strong><small>{branch.agent_id} · {branch.conflicting_keys.length} conflicting key(s)</small></div><button className="text-action" onClick={()=>void openResolve(branch)}>Review <span>→</span></button></div>):<div className="empty-state compact"><div className="empty-check">✓</div><strong>No conflicts to resolve</strong><p>Branches are clear to merge.</p></div>}
              <button className="card-footer-link" onClick={()=>{setTab("Branches");setBranchStatus("open")}}>View all branches <span>→</span></button>
            </section>
          </div>
          <section className="surface-card recent-card">
            <div className="surface-heading"><div><h2>Recent activity</h2><p>Latest events recorded by the coordination runtime</p></div><button className="button-secondary compact-button" onClick={()=>setTab("Event log")}>Open event log</button></div>
            {events.slice(0,6).length?<div className="data-table-wrap"><table className="data-table"><thead><tr><th>EVENT</th><th>AGENT</th><th>EVENT ID</th><th>TIME</th></tr></thead><tbody>{events.slice(0,6).map(event=><tr key={event.event_id}><td><span className="event-name"><i className={/conflict|abort|reject/.test(event.action)?"event-dot danger":/commit|resolve/.test(event.action)?"event-dot success":"event-dot"}/>{event.action}</span></td><td>{event.agent_id}</td><td><code>{short(event.event_id)}</code></td><td>{timeAgo(event.timestamp)}</td></tr>)}</tbody></table></div>:<div className="empty-state"><strong>No activity recorded yet</strong><p>Create a branch or acquire a lease to start recording coordination events.</p></div>}
          </section>
        </>}

        {tab==="Branches"&&<>
          <div className="page-heading"><div><div className="eyebrow">WORKSPACE / COORDINATION</div><h1>Branches</h1><p>Isolated workspaces where agents can make changes without overwriting one another.</p></div><button className="button-primary" onClick={()=>setCreateOpen(true)}><span className="button-icon"><GitBranch size={14}/></span> Create branch</button></div>
          <div className="branch-controls"><div className="search-control"><span>⌕</span><input value={filter} onChange={e=>setFilter(e.target.value)} placeholder="Search branches or agents"/></div><div className="segmented-control"><button className={branchStatus==="open"?"active":""} onClick={()=>{setBranchStatus("open");setSelected([])}}>Open <b>{openBranches.length}</b></button><button className={branchStatus==="merged"?"active":""} onClick={()=>{setBranchStatus("merged");setSelected([])}}>Merged</button></div></div>
          <div className="table-toolbar"><span>{visibleBranches.length} branches</span><button className="button-secondary" disabled={!selected.length||busy} onClick={()=>void run(async()=>{for(const id of selected){const b=branches.find(x=>x.id===id);if(b){const result=await api<any>(`/branches/${b.id}/commit`,{method:"POST"});if(result.conflict)throw new Error(`Conflict in ${b.name}: ${result.conflicting_keys.join(", ")}`)}}setSelected([])},"Selected branches merged")}>Merge selected ({selected.length})</button></div>
          <section className="surface-card table-surface"><div className="data-table-wrap"><table className="data-table"><thead><tr><th><input type="checkbox" checked={visibleBranches.length>0&&visibleBranches.every(b=>selected.includes(b.id))} onChange={e=>setSelected(e.target.checked?visibleBranches.filter(b=>!b.conflicting_keys.length).map(b=>b.id):[])}/></th><th>BRANCH</th><th>OWNER</th><th>BASE VERSION</th><th>STATUS</th><th>CREATED</th><th/></tr></thead><tbody>{visibleBranches.map(branch=><tr key={branch.id}><td><input type="checkbox" disabled={branch.conflicting_keys.length>0} checked={selected.includes(branch.id)} onChange={e=>setSelected(prev=>e.target.checked?[...prev,branch.id]:prev.filter(id=>id!==branch.id))}/></td><td><strong>{branch.name}</strong><small>{branch.id.slice(0,8)}</small></td><td>{branch.agent_id}</td><td><code>{short(branch.base_version)}</code></td><td><span className={branch.status==="merged"?"status-tag success":branch.conflicting_keys.length?"status-tag danger":"status-tag neutral"}><i/>{branch.status==="merged"?"Merged":branch.conflicting_keys.length?"Conflict":"Open"}</span></td><td>{timeAgo(branch.created_at)}</td><td>{branch.status==="open"?(branch.conflicting_keys.length?<button className="text-action" onClick={()=>void openResolve(branch)}>Resolve →</button>:<button className="text-action" disabled={busy} onClick={()=>void mergeBranch(branch)}>Merge →</button>):"—"}</td></tr>)}{!visibleBranches.length&&<tr><td colSpan={7}><div className="empty-state"><strong>No branches found</strong><p>Create a branch to give an agent an isolated place to work.</p></div></td></tr>}</tbody></table></div></section>
        </>}

        {tab==="State"&&<>
          <div className="page-heading"><div><div className="eyebrow">WORKSPACE / SHARED MEMORY</div><h1>Shared state</h1><p>A content-addressed view of the values agents read and write together.</p></div><span className="state-head-label">HEAD <code>{short(state.head)}</code></span></div>
          <section className="surface-card"><div className="surface-heading"><div><h2>Workspace keys</h2><p>{state.items.length} keys in the current snapshot</p></div><span className="subtle-tag">CONTENT ADDRESSED</span></div><div className="data-table-wrap"><table className="data-table"><thead><tr><th>KEY</th><th>VALUE HASH</th><th>VALUE PREVIEW</th></tr></thead><tbody>{state.items.map(item=><tr key={item.key}><td><strong className="mono-text">{item.key}</strong></td><td><code>{short(item.value_hash)}</code></td><td><code className="value-preview">{JSON.stringify(item.value)}</code></td></tr>)}{!state.items.length&&<tr><td colSpan={3}><div className="empty-state"><strong>Shared state is empty</strong><p>Seed a workspace through the Cohort runtime before writing branch data.</p></div></td></tr>}</tbody></table></div></section>
        </>}

        {tab==="Event log"&&<>
          <div className="page-heading"><div><div className="eyebrow">WORKSPACE / AUDIT TRAIL</div><h1>Event log</h1><p>An ordered record of coordination decisions, writes, leases and branch operations.</p></div><button className="button-secondary" onClick={()=>{const blob=new Blob([events.map(e=>JSON.stringify(e)).join("\\n")],{type:"application/x-ndjson"});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download="cohort-events.jsonl";a.click();URL.revokeObjectURL(url)}}>↓ Export JSONL</button></div>
          <div className="branch-controls"><div className="search-control"><span>⌕</span><input value={filter} onChange={e=>setFilter(e.target.value)} placeholder="Filter by event, agent or ID"/></div><span className="event-total">{events.length} events loaded</span></div>
          <section className="surface-card"><div className="data-table-wrap"><table className="data-table"><thead><tr><th>EVENT</th><th>AGENT</th><th>EVENT ID</th><th>RECORDED AT</th><th/></tr></thead><tbody>{events.filter(e=>(e.action+" "+e.agent_id+" "+e.event_id).toLowerCase().includes(filter.toLowerCase())).map(event=><tr key={event.event_id}><td><span className="event-name"><i className={/conflict|abort|reject/.test(event.action)?"event-dot danger":/commit|resolve/.test(event.action)?"event-dot success":"event-dot"}/>{event.action}</span></td><td>{event.agent_id}</td><td><code>{short(event.event_id)}</code></td><td>{new Date(event.timestamp).toLocaleString()}</td><td><button className="text-action" onClick={()=>{setReplayIndex(events.findIndex(e=>e.event_id===event.event_id));setSidebar(true)}}>Inspect →</button></td></tr>)}</tbody></table></div></section>
        </>}

        {tab==="Settings"&&<>
          <div className="page-heading"><div><div className="eyebrow">WORKSPACE / CONFIGURATION</div><h1>Runtime settings</h1><p>Inspect the configuration and operational boundaries of this Cohort instance.</p></div></div>
          <div className="settings-layout"><section className="surface-card"><div className="surface-heading"><div><h2>Storage and coordination</h2><p>Current runtime configuration</p></div></div><Setting label="Storage backend" value={settings?.persistence||"—"}/><Setting label="Database path" value={settings?.database_path||"—"}/><Setting label="Lease enforcement" value={settings?(settings.require_leases?"Required for writes":"Advisory"):"—"}/></section><section className="surface-card"><div className="surface-heading"><div><h2>Runtime capabilities</h2><p>Features reported by the API adapter</p></div></div><Setting label="Multi-process coordination" value={settings?(settings.multi_process?"Enabled":"Single process"):"—"}/><Setting label="Authentication" value={settings?(settings.authentication?"Enabled":"Not configured"):"—"}/><div className="security-notice"><strong>Deployment note</strong><p>The current adapter is intended for local development. Do not expose it publicly without authentication, authorization, tenant isolation and a durable branch registry.</p></div></section></div>
        </>}
      </main>
    </div>

    {sidebar&&<div className="inspector-backdrop" onClick={()=>setSidebar(false)}><aside className="inspector-panel" onClick={e=>e.stopPropagation()}><div className="inspector-header"><div><span className="eyebrow">RUNTIME INSPECTOR</span><h2>Execution details</h2></div><button className="topbar-icon" onClick={()=>setSidebar(false)}>×</button></div><p className="inspector-intro">Inspect the underlying coordination primitives and event data.</p>
      <details open><summary>Event replay</summary><div className="inspector-body"><input type="range" min="0" max={Math.max(0,events.length-1)} value={replayIndex} onChange={e=>setReplayIndex(Number(e.target.value))}/>{replayEvent?<><div className="inspector-meta"><span>EVENT {replayIndex+1} / {events.length}</span><span>{short(state.head)}</span></div><pre className="code-block">{JSON.stringify(replayEvent,null,2)}</pre></>:<p className="empty-copy">No events recorded.</p>}</div></details>
      <details><summary>Snapshots</summary><div className="inspector-body"><div className="inspector-record"><strong>{short(state.head)}</strong><small>Current HEAD · {state.items.length} keys</small></div>{state.parent&&<div className="inspector-record"><strong>{short(state.parent)}</strong><small>Parent snapshot</small></div>}</div></details>
      <details><summary>Leases</summary><div className="inspector-body">{leases.length?leases.map(lease=><div className="inspector-record" key={lease.key}><strong>{lease.key}</strong><small>{lease.agent_id} · fencing token {lease.fencing_token}</small><button className="button-secondary compact-button" onClick={()=>void releaseLease(lease)}>Release lease</button></div>):<p className="empty-copy">No active leases.</p>}<label className="form-label">Agent ID<input value={leaseAgent} onChange={e=>setLeaseAgent(e.target.value)}/></label><label className="form-label">Resource key<input value={leaseKey} onChange={e=>setLeaseKey(e.target.value)} placeholder="shared/resource"/></label><button className="button-primary full-button" disabled={busy||!leaseKey.trim()} onClick={acquireLease}>Acquire 60s lease</button></div></details>
      <details><summary>Trace analyzer</summary><div className="inspector-body"><p className="empty-copy">Load an exported JSONL event trace.</p><input type="file" accept=".jsonl,.json,.txt" onChange={e=>{const file=e.target.files?.[0];if(file)void file.text().then(parseTrace)}}/><textarea rows={3} value={traceText} onChange={e=>setTraceText(e.target.value)} placeholder="Paste JSONL events…"/><button className="button-secondary compact-button" onClick={()=>parseTrace(traceText||events.map(e=>JSON.stringify(e)).join("\\n"))}>Analyze events</button>{trace&&Object.entries(trace.actions).map(([action,count])=><div className="inspector-meta" key={action}><span>{action}</span><strong>{count}</strong></div>)}</div></details>
      <details><summary>MCP and persistence</summary><div className="inspector-body"><div className="inspector-meta"><span>API</span><strong>{connected?"Connected":"Offline"}</strong></div><div className="inspector-meta"><span>Storage</span><strong>{settings?.persistence||"—"}</strong></div><div className="inspector-meta"><span>MCP</span><strong>Local stdio</strong></div><p className="empty-copy">MCP is currently a local stdio integration, not a hosted multi-user service.</p></div></details>
    </aside></div>}

    {createOpen&&<div className="modal-backdrop" onClick={()=>setCreateOpen(false)}><div className="modal-card" onClick={e=>e.stopPropagation()}><div className="modal-head"><div><span className="eyebrow">WORKSPACE / BRANCHES</span><h2>Create branch</h2></div><button className="topbar-icon" onClick={()=>setCreateOpen(false)}>×</button></div><p className="modal-description">Give an agent an isolated branch to work in.</p><label className="form-label">Agent ID<input value={agentId} onChange={e=>setAgentId(e.target.value)} placeholder="agent-backend"/></label><label className="form-label">Branch name<input value={branchName} onChange={e=>setBranchName(e.target.value)} placeholder="implement-api"/></label><div className="modal-actions"><button className="button-secondary" onClick={()=>setCreateOpen(false)}>Cancel</button><button className="button-primary" disabled={busy||!agentId.trim()||!branchName.trim()} onClick={()=>void createBranch()}>Create branch</button></div></div></div>}
    {resolveBranch&&<div className="modal-backdrop" onClick={()=>setResolveBranch(null)}><div className="modal-card resolve-modal" onClick={e=>e.stopPropagation()}><div className="modal-head"><div><span className="eyebrow">CONFLICT REVIEW</span><h2>Resolve {resolveBranch.name}</h2></div><button className="topbar-icon" onClick={()=>setResolveBranch(null)}>×</button></div><p className="modal-description">Review the competing values before applying a resolution.</p>{conflictDetails.map(detail=><div className="conflict-context" key={detail.key}><strong>{detail.key}</strong><div className="three-way">{([{label:"Base",value:detail.base,present:detail.base_present},{label:"HEAD",value:detail.head,present:detail.head_present},{label:"Branch",value:detail.branch,present:detail.branch_present}]).map(item=><div key={item.label}><span>{item.label}</span><pre>{item.present?JSON.stringify(item.value,null,2):"∅ absent"}</pre></div>)}</div></div>)}<label className="form-label">Resolution strategy<select value={strategy} onChange={e=>setStrategy(e.target.value)}><option>PreferHead</option><option>PreferBranch</option><option>PreferAgent</option></select></label>{strategy==="PreferAgent"&&<label className="form-label">Agent priority<input value={agentPriority} onChange={e=>setAgentPriority(e.target.value)} placeholder="agent-backend, agent-frontend"/></label>}<label className="form-label">Decision rationale<textarea rows={3} value={rationale} onChange={e=>setRationale(e.target.value)} placeholder="Explain why this resolution is appropriate."/></label><div className="security-notice"><strong>Review required</strong><p>The resolver applies a deterministic policy. It cannot determine whether the resulting code is semantically correct.</p></div><div className="modal-actions"><button className="button-secondary" onClick={()=>setResolveBranch(null)}>Cancel</button><button className="button-primary" disabled={busy||!rationale.trim()} onClick={()=>void resolve()}>Record resolution</button></div></div></div>}
    {notice&&<div className="toast">{notice}</div>}
  </div>;
}

function Metric({ label, value, tone }: { label: string; value: string | number; tone?: string }) { return <div className="metric-card"><span>{label}</span><strong className={tone || ""}>{value}</strong></div>; }
function Setting({ label, value }: { label: string; value: string }) { return <div className="setting-line"><span>{label}</span><code>{value}</code></div>; }
