import { useCallback, useEffect, useMemo, useState } from "react";
import "./cohort-dashboard.css";

type Tab = "Overview" | "Branches" | "State" | "Settings";
type EventItem = { event_id: string; timestamp: string; agent_id: string; action: string; payload: Record<string, unknown>; schema_version: string };
type Branch = { id: string; name: string; agent_id: string; base_version: string; status: string; conflicting_keys: string[]; created_at: string };
type StateItem = { key: string; value_hash: string; value: unknown };
type Lease = { key: string; agent_id: string; expires_at: number; acquired_at: number; fencing_token: number };
type Overview = { head: string; key_count: number; snapshot_count: number; event_count: number; active_lease_count: number; commit_count: number; conflict_count: number; branches: number; sample_data: boolean };
type Settings = { require_leases: boolean; persistence: string; database_path: string; multi_process: boolean; authentication: boolean };

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
  const [sidebar, setSidebar] = useState(true);
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
  const [activeEvent, setActiveEvent] = useState<EventItem | null>(null);
  const [replayIndex, setReplayIndex] = useState(0);
  const [resolveBranch, setResolveBranch] = useState<Branch | null>(null);
  const [strategy, setStrategy] = useState("PreferHead");
  const [rationale, setRationale] = useState("");
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
      setActiveEvent((current) => current ? (e.items.find((x) => x.event_id === current.event_id) || current) : (e.items[0] || null));
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
      await api(`/branches/${resolveBranch.id}/resolve`, { method: "POST", body: JSON.stringify({ strategy, rationale }) });
      setResolveBranch(null); setRationale("");
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

  return <div className={`cohort-app ${dark ? "is-dark" : ""}`}>
    {banner && <div className="sample-banner"><span><b>{connected ? "Runtime connected." : "Runtime disconnected."}</b> {connected ? "Values below are read from the Cohort API." : "Start the Python API to load live workspace data."}</span><button onClick={() => setBanner(false)} aria-label="Dismiss">×</button></div>}
    <header className="cohort-header">
      <div className="cohort-brand">
        <svg width="28" height="28" viewBox="0 0 200 200" aria-hidden="true"><circle cx="100" cy="65" r="50" fill="#8B5CF6"/><circle cx="70" cy="117" r="50" fill="#14B8A6" opacity=".95"/><circle cx="130" cy="117" r="50" fill="#FB7185" opacity=".95"/><circle cx="100" cy="100" r="22" fill="currentColor"/></svg>
        <b>cerbere, inc</b><span className="admin-chip">Admin</span>
      </div>
      <div className="header-spacer"/>
      <span className={connected ? "connection-state online" : "connection-state"}><i/> {connected ? "API connected" : "API offline"}</span>
      <button className="icon-btn" title="Toggle theme" onClick={() => setDark(!dark)}>◐</button>
      <button className="icon-btn" title="Under the hood" onClick={() => setSidebar(!sidebar)}>?</button>
      <div className="user-avatar">C</div>
    </header>
    <div className="dashboard-shell">
      <aside className={`under-sidebar ${sidebar ? "" : "is-closed"}`}>
        <div className="under-inner">
          <h2>Under the hood <button className="icon-btn" onClick={() => setSidebar(false)} aria-label="Close">×</button></h2>
          <p className="under-sub">What Cohort does beyond branches and conflicts.</p>
          <details open><summary>Event log and replay</summary><div className="under-body">
            <input type="range" min="0" max={Math.max(0, events.length - 1)} value={replayIndex} onChange={(e) => setReplayIndex(Number(e.target.value))}/>
            {replayEvent ? <><div className="kv"><span>event {replayIndex + 1} of {events.length}</span><span>head {short(state.head)}</span></div><pre className="code-block">{JSON.stringify(replayEvent, null, 2)}</pre><div className="success-note">✓ Event loaded from runtime log</div></> : <p className="empty-note">No events have been recorded yet.</p>}
          </div></details>
          <details><summary>Snapshots</summary><div className="under-body">
            <div className="snapshot-entry"><b>{short(state.head)}</b><small>Current workspace HEAD · {state.items.length} keys</small></div>
            {state.parent && <div className="snapshot-entry"><b>{short(state.parent)}</b><small>Parent snapshot</small></div>}
            <p className="empty-note">Snapshots are derived from the runtime's content-addressed history.</p>
          </div></details>
          <details><summary>Conflict resolution</summary><div className="under-body">
            {conflicts.length ? conflicts.map((branch) => <div className="snapshot-entry" key={branch.id}><b>{branch.name}</b><small>{branch.conflicting_keys.join(", ")}</small><button className="small-button" onClick={() => setResolveBranch(branch)}>Resolve conflict</button></div>) : <p className="empty-note">No unresolved branch conflicts.</p>}
            <p className="empty-note">A resolver is a policy choice, not proof that the resulting content is correct.</p>
          </div></details>
          <details><summary>Leases</summary><div className="under-body">
            {leases.length ? leases.map((lease) => <div className="lease-mini" key={lease.key}><b>{lease.key}</b><span>{lease.agent_id}</span><small>token {lease.fencing_token} · expires {dateTime(lease.expires_at)}</small></div>) : <p className="empty-note">No active leases.</p>}
            <label className="field-label">Agent ID<input value={leaseAgent} onChange={(e) => setLeaseAgent(e.target.value)}/></label>
            <label className="field-label">Resource key<input value={leaseKey} onChange={(e) => setLeaseKey(e.target.value)} placeholder="shared/resource"/></label>
            <button className="primary-btn" onClick={acquireLease} disabled={busy || !leaseKey.trim()}>Acquire 60s lease</button>
          </div></details>
          <details><summary>Deadlock detection</summary><div className="under-body">
            <div className={`deadlock-visual ${deadlock ? "cycle" : ""}`}><span>backend</span><span>database</span><span>frontend</span></div>
            <p className={deadlock ? "error-note" : "success-note"}>{deadlock ? "Illustrative wait-for cycle: backend → database → frontend → backend." : "No simulated cycle. Deadlock detection runs in the runtime when agents wait for leases."}</p>
            <button className="small-button" onClick={() => setDeadlock(!deadlock)}>{deadlock ? "Clear simulation" : "Simulate cycle"}</button>
          </div></details>
          <details><summary>Trace analyzer</summary><div className="under-body">
            <p className="empty-note">Load an exported events.jsonl file.</p><input type="file" accept=".jsonl,.json,.txt" onChange={(e) => { const file = e.target.files?.[0]; if (file) void file.text().then(parseTrace); }}/>
            <button className="small-button" onClick={() => parseTrace(traceText || events.map((event) => JSON.stringify(event)).join("\n"))}>Analyze current events</button>
            <textarea rows={3} value={traceText} onChange={(e) => setTraceText(e.target.value)} placeholder="Paste JSONL events…"/>
            {trace && <><div className="kv"><span>Actions</span><b>{Object.values(trace.actions).reduce((a, b) => a + b, 0)}</b></div>{Object.entries(trace.actions).map(([action, count]) => <div className="kv" key={action}><span>{action}</span><b>{count}</b></div>)}{trace.bad > 0 && <p className="error-note">{trace.bad} unreadable lines</p>}</>}
          </div></details>
          <details><summary>MCP and persistence</summary><div className="under-body">
            <div className="kv"><span>Runtime API</span><b>{connected ? "connected" : "offline"}</b></div>
            <div className="kv"><span>Persistence</span><b>{settings?.persistence || "—"}</b></div>
            <div className="kv"><span>MCP server</span><b>stdio prototype</b></div>
            <p className="empty-note">The MCP integration currently runs as a local stdio process. It is not exposed as a multi-user HTTP service.</p>
          </div></details>
        </div>
      </aside>
      <main className="cohort-main">
        <nav className="cohort-tabs">
          <button className="tab-control" onClick={() => setSidebar(!sidebar)} title="Toggle technical panel">{sidebar ? "◨" : "◧"}</button>
          {(["Overview", "Branches", "State", "Settings"] as Tab[]).map((item) => <button key={item} className={tab === item ? "cohort-tab active" : "cohort-tab"} onClick={() => setTab(item)}>{item}</button>)}
          <span className="tabs-spacer"/>
          <button className="small-button" onClick={() => void refresh()}>Refresh</button>
        </nav>
        <div className="cohort-content">
          {error && <div className="api-error"><b>Cannot load runtime data.</b> {error} <span>API expected at {API || "the current origin"}/api</span></div>}
          {tab === "Overview" && <>
            <div className="toolbar"><div className="scope-label">Workspace / main</div><button className="dark-btn" onClick={() => { const blob = new Blob([events.map((e) => JSON.stringify(e)).join("\n")], { type: "application/x-ndjson" }); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = "cohort-events.jsonl"; a.click(); URL.revokeObjectURL(url); }}>Export events</button></div>
            <div className="sub-tabs">{(["Coordination", "Conflicts"] as const).map((item) => <button key={item} className={sub === item ? "selected" : ""} onClick={() => setSub(item)}>{item}</button>)}</div>
            <div className="metric-grid">
              <Metric label="Workspace keys" value={overview?.key_count ?? "—"}/>
              <Metric label="Snapshots" value={overview?.snapshot_count ?? "—"}/>
              <Metric label="Active leases" value={overview?.active_lease_count ?? "—"}/>
              <Metric label="Conflicts detected" value={overview?.conflict_count ?? "—"} tone={conflicts.length ? "red" : "green"}/>
            </div>
            {sub === "Coordination" ? <div className="chart-grid">
              <section className="panel"><PanelTitle title="Commits and coordination events" right="Last 14 days"/><div className="chart-wrap"><BarChart values={actionCounts.map((d) => d.commits)} tone="teal" labels={actionCounts.map((d) => d.label)}/></div><div className="panel-foot"><b>Top shared keys by write activity</b>{state.items.slice(0, 4).map((item) => <div className="rank-row" key={item.key}><span>{item.key}</span><i style={{ width: `${Math.max(5, (item.key.length / 40) * 100)}%` }}/><small>{short(item.value_hash)}</small></div>)}</div></section>
              <section className="panel"><PanelTitle title="Conflicts detected" right="Last 14 days"/><div className="chart-wrap"><BarChart values={actionCounts.map((d) => d.conflicts)} tone="coral" labels={actionCounts.map((d) => d.label)}/></div><div className="panel-foot"><b>Open conflicting branches</b>{conflicts.length ? conflicts.map((branch) => <div className="rank-row" key={branch.id}><span>{branch.name}</span><i className="coral-bar" style={{ width: `${Math.min(100, branch.conflicting_keys.length * 30)}%` }}/><small>{branch.conflicting_keys.length} keys</small></div>) : <p className="empty-note">No unresolved conflicts.</p>}</div></section>
            </div> : <div className="panel conflict-overview"><PanelTitle title="Unresolved branch conflicts" right={`${conflicts.length} open`}/>{conflicts.length ? conflicts.map((branch) => <div className="conflict-overview-row" key={branch.id}><div><b>{branch.name}</b><small>{branch.agent_id} · {branch.conflicting_keys.join(", ")}</small></div><button className="small-button" onClick={() => setResolveBranch(branch)}>Review resolution</button></div>) : <p className="empty-note">No unresolved conflicts have been reported by the runtime.</p>}</div>}
            <div className="panel recent-events"><PanelTitle title="Recent runtime events" right={`${events.length} loaded`}/>{events.slice(0, 6).map((event) => <button className="event-line" key={event.event_id} onClick={() => { setActiveEvent(event); setSidebar(true); }}><i/><b>{event.action}</b><span>{event.agent_id}</span><time>{timeAgo(event.timestamp)}</time></button>)}{!events.length && <p className="empty-note">No events yet. Create a branch or acquire a lease to generate the first runtime events.</p>}</div>
          </>}
          {tab === "Branches" && <><div className="branch-toolbar"><div className="search-input"><span>⌕</span><input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter branches by name or agent…"/></div><div className="segmented"><button className={branchStatus === "open" ? "on" : ""} onClick={() => { setBranchStatus("open"); setSelected([]); }}>Open</button><button className={branchStatus === "merged" ? "on" : ""} onClick={() => { setBranchStatus("merged"); setSelected([]); }}>Merged</button></div><button className="primary-btn" onClick={() => setCreateOpen(true)}>+ New branch</button></div>
            <div className="suggestions">Filter by <button onClick={() => setFilter("frontend")}>frontend</button><button onClick={() => setFilter("security")}>security</button><button onClick={() => setFilter("")}>clear</button></div>
            <div className="branch-actions"><span>{visibleBranches.length} branches</span><span className="tabs-spacer"/><button className="dark-btn" disabled={!selected.length || busy} onClick={() => void run(async () => { for (const id of selected) { const b = branches.find((x) => x.id === id); if (b) { const result = await api<any>(`/branches/${b.id}/commit`, { method: "POST" }); if (result.conflict) throw new Error(`Conflict in ${b.name}: ${result.conflicting_keys.join(", ")}`); } } setSelected([]); }, "Selected branches merged")}>Merge selected</button></div>
            <div className="panel table-scroll"><table><thead><tr><th><input type="checkbox" checked={visibleBranches.length > 0 && visibleBranches.every((b) => selected.includes(b.id))} onChange={(e) => setSelected(e.target.checked ? visibleBranches.filter((b) => !b.conflicting_keys.length).map((b) => b.id) : [])}/></th><th>Branch</th><th>Merge status</th><th>Created</th><th>Actions</th></tr></thead><tbody>{visibleBranches.map((branch) => <tr key={branch.id}><td><input type="checkbox" disabled={branch.conflicting_keys.length > 0} checked={selected.includes(branch.id)} onChange={(e) => setSelected((prev) => e.target.checked ? [...prev, branch.id] : prev.filter((id) => id !== branch.id))}/></td><td><b>{branch.name}</b><small>{branch.id.slice(0, 8)} · {branch.agent_id} · base {short(branch.base_version)}</small></td><td><span className={`status-dot-label ${branch.conflicting_keys.length ? "danger" : branch.status === "merged" ? "good" : ""}`}>{branch.status === "merged" ? "Merged" : branch.conflicting_keys.length ? `Conflict · ${branch.conflicting_keys.length} key(s)` : "Not merged"}</span></td><td>{timeAgo(branch.created_at)}</td><td>{branch.status === "open" ? branch.conflicting_keys.length ? <button className="small-button" onClick={() => setResolveBranch(branch)}>Resolve</button> : <button className="small-button" disabled={busy} onClick={() => void mergeBranch(branch)}>Merge</button> : "—"}</td></tr>)}{!visibleBranches.length && <tr><td colSpan={5} className="empty-cell">No branches in this view. Create one to start coordinating work.</td></tr>}</tbody></table></div>
          </>}
          {tab === "State" && <><h1>Shared state</h1><p className="page-intro">Current head <code>{short(state.head)}</code> · {state.items.length} keys · content-addressed values.</p><div className="panel table-scroll"><table><thead><tr><th>Key</th><th>Value hash</th><th>Value preview</th></tr></thead><tbody>{state.items.map((item) => <tr key={item.key}><td><b className="mono">{item.key}</b></td><td className="mono">{short(item.value_hash)}</td><td><code className="value-preview">{JSON.stringify(item.value)}</code></td></tr>)}{!state.items.length && <tr><td colSpan={3} className="empty-cell">Shared state is empty. Seed a workspace through the Python API before writing branches.</td></tr>}</tbody></table></div></>}
          {tab === "Settings" && <><h1>Runtime settings</h1><p className="page-intro">Current configuration reported by the Cohort API.</p><div className="settings-grid"><section className="panel setting-card"><PanelTitle title="Workspace and persistence"/><Setting label="Storage backend" value={settings?.persistence || "—"}/><Setting label="Database path" value={settings?.database_path || "—"}/><Setting label="Lease enforcement" value={settings ? settings.require_leases ? "Required for writes" : "Advisory" : "—"}/></section><section className="panel setting-card"><PanelTitle title="Runtime limitations"/><Setting label="Multi-process coordination" value={settings ? settings.multi_process ? "Enabled" : "Not supported" : "—"}/><Setting label="Authentication" value={settings ? settings.authentication ? "Enabled" : "Not configured" : "—"}/><p className="warning-copy">The current API adapter is a single-process integration. Do not expose it publicly without authentication, authorization, tenant isolation and a durable branch registry.</p></section></div></>}
        </div>
      </main>
    </div>
    {createOpen && <div className="modal-backdrop" onClick={() => setCreateOpen(false)}><div className="modal-card" onClick={(e) => e.stopPropagation()}><div className="modal-head"><h2>Create branch</h2><button className="icon-btn" onClick={() => setCreateOpen(false)}>×</button></div><label className="field-label">Agent ID<input value={agentId} onChange={(e) => setAgentId(e.target.value)} placeholder="agent-backend"/></label><label className="field-label">Branch name<input value={branchName} onChange={(e) => setBranchName(e.target.value)} placeholder="implement-api"/></label><div className="modal-actions"><button className="small-button" onClick={() => setCreateOpen(false)}>Cancel</button><button className="primary-btn" disabled={busy || !agentId.trim() || !branchName.trim()} onClick={() => void createBranch()}>Create branch</button></div></div></div>}
    {resolveBranch && <div className="modal-backdrop" onClick={() => setResolveBranch(null)}><div className="modal-card" onClick={(e) => e.stopPropagation()}><div className="modal-head"><h2>Resolve {resolveBranch.name}</h2><button className="icon-btn" onClick={() => setResolveBranch(null)}>×</button></div><p className="page-intro">Conflicting keys: {resolveBranch.conflicting_keys.join(", ")}</p><label className="field-label">Resolution strategy<select value={strategy} onChange={(e) => setStrategy(e.target.value)}><option>PreferHead</option><option>PreferBranch</option><option>PreferAgent</option></select></label><label className="field-label">Rationale<textarea rows={3} value={rationale} onChange={(e) => setRationale(e.target.value)} placeholder="Explain why this side should be retained."/></label><p className="warning-copy">The selected resolver decides conflicting values. Review the result in your application; Cohort cannot verify semantic correctness.</p><div className="modal-actions"><button className="small-button" onClick={() => setResolveBranch(null)}>Cancel</button><button className="primary-btn" disabled={busy || !rationale.trim()} onClick={() => void resolve()}>Record decision</button></div></div></div>}
    {notice && <div className="toast">{notice}</div>}
  </div>;
}

function Metric({ label, value, tone }: { label: string; value: string | number; tone?: string }) { return <div className="metric-card"><small>{label}</small><strong className={tone || ""}>{value}</strong></div>; }
function PanelTitle({ title, right }: { title: string; right?: string }) { return <div className="panel-title"><span>{title}</span>{right && <small>{right}</small>}</div>; }
function Setting({ label, value }: { label: string; value: string }) { return <div className="setting-line"><span>{label}</span><code>{value}</code></div>; }
function BarChart({ values, tone, labels }: { values: number[]; tone: "teal" | "coral"; labels: string[] }) {
  const max = Math.max(1, ...values);
  return <div className="bar-chart"><div className="chart-y"><span>{max}</span><span>{Math.round(max / 2)}</span><span>0</span></div><div className="bars">{values.map((value, i) => <div className="bar-column" key={i}><div className={`bar ${tone}`} style={{ height: `${Math.max(2, value / max * 100)}%` }} title={`${labels[i]}: ${value}`}/><small>{i % 2 === 0 ? labels[i] : ""}</small></div>)}</div></div>;
}
