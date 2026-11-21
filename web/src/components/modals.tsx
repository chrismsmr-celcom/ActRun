import { useEffect, useState } from "react";
import { Shield } from "lucide-react";
import { api, isUnavailable, PLANS_URL } from "../lib/api";
import { clock, timeAgo } from "../lib/format";
import { useOptional } from "../lib/useCohort";
import type { Branch, BranchDiff, CerbereSummary, ConflictDetail, EventItem, Plan, PlansResponse } from "../lib/types";
import { Empty, Json, Modal, Seg, Skeleton, Tag, useToast } from "./ui";
import cerbereIcon from "../assets/cerbere-ag.png";

export type Run = (action: () => Promise<unknown>, success: string) => Promise<boolean>;

export function CreateBranchModal({ onClose, run, busy }: { onClose: () => void; run: Run; busy: boolean }) {
  const [agent, setAgent] = useState("agent-new"); const [name, setName] = useState("");
  const submit = async () => { if (await run(() => api<Branch>("/branches", { method: "POST", body: JSON.stringify({ agent_id: agent.trim(), name: name.trim() }) }), "Branch created")) onClose(); };
  return <Modal title="Create branch" description="Give an agent an isolated branch to work in." onClose={onClose}
    footer={<><button className="btn btn-secondary" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy || !agent.trim() || !name.trim()} onClick={() => void submit()}>Create branch</button></>}>
    <label className="field">Agent ID<input autoFocus value={agent} onChange={(e) => setAgent(e.target.value)} placeholder="agent-backend" /></label>
    <label className="field">Branch name<input value={name} onChange={(e) => setName(e.target.value)} placeholder="implement-api" onKeyDown={(e) => { if (e.key === "Enter" && agent.trim() && name.trim()) void submit(); }} /></label>
  </Modal>;
}

export function WriteModal({ branch, onClose, run, busy }: { branch: Branch; onClose: () => void; run: Run; busy: boolean }) {
  const toast = useToast();
  const [key, setKey] = useState(""); const [value, setValue] = useState(""); const [intent, setIntent] = useState("");
  const submit = async () => {
    let parsed: unknown;
    try { parsed = JSON.parse(value); } catch { toast('Value must be valid JSON, e.g. "text", 42 or {"a": 1}', "err"); return; }
    if (await run(() => api(`/branches/${branch.id}/state`, { method: "PUT", body: JSON.stringify({ key: key.trim(), value: parsed, intent: intent.trim() || null }) }), "Value written to branch")) onClose();
  };
  return <Modal title="Write a value" description={`Changes stay isolated in “${branch.name}” until it is merged.`} onClose={onClose}
    footer={<><button className="btn btn-secondary" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy || !key.trim() || !value.trim()} onClick={() => void submit()}>Write value</button></>}>
    <label className="field">Key<input autoFocus value={key} onChange={(e) => setKey(e.target.value)} placeholder="config/database" /></label>
    <label className="field">Value (JSON)<textarea rows={4} value={value} onChange={(e) => setValue(e.target.value)} placeholder='{"host": "db.internal", "pool": 10}' className="data" /></label>
    <label className="field">Intent <small>Optional — why this change is made</small><input value={intent} onChange={(e) => setIntent(e.target.value)} /></label>
  </Modal>;
}

const ThreeWay = ({ items }: { items: { label: string; value: unknown; present: boolean }[] }) =>
  <div className="three">{items.map((i) => <div key={i.label}><small>{i.label}</small><pre className="code" style={{ maxHeight: 160 }}>{i.present ? JSON.stringify(i.value, null, 2) : "∅ absent"}</pre></div>)}</div>;

export function ResolveModal({ branch, onClose, run, busy }: { branch: Branch; onClose: () => void; run: Run; busy: boolean }) {
  const toast = useToast();
  const [details, setDetails] = useState<ConflictDetail[] | null>(null);
  const [strategy, setStrategy] = useState("PreferHead"); const [rationale, setRationale] = useState(""); const [priority, setPriority] = useState("");
  useEffect(() => {
    let active = true;
    api<{ conflicts: ConflictDetail[] }>(`/branches/${branch.id}/conflict`).then((d) => { if (active) setDetails(d.conflicts); }).catch((e) => { if (active) { setDetails([]); toast(e instanceof Error ? e.message : "Could not load conflict details", "err"); } });
    return () => { active = false; };
  }, [branch.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const submit = async () => {
    if (await run(() => api(`/branches/${branch.id}/resolve`, { method: "POST", body: JSON.stringify({ strategy, rationale, priority: priority.split(",").map((x) => x.trim()).filter(Boolean) }) }), "Resolution recorded and branch committed")) onClose();
  };
  return <Modal size="wide" title={`Resolve ${branch.name}`} description="Review the competing values before applying a resolution." onClose={onClose}
    footer={<><button className="btn btn-secondary" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy || !rationale.trim()} onClick={() => void submit()}>Record resolution</button></>}>
    {details === null ? <div className="stack" aria-busy="true"><Skeleton h={24} w="40%" /><Skeleton h={96} /></div>
      : details.map((d) => <div className="stack" key={d.key}><strong className="data">{d.key}</strong>
        <ThreeWay items={[{ label: "Base", value: d.base, present: d.base_present }, { label: "HEAD", value: d.head, present: d.head_present }, { label: "Branch", value: d.branch, present: d.branch_present }]} /></div>)}
    <label className="field">Resolution strategy<select value={strategy} onChange={(e) => setStrategy(e.target.value)}><option>PreferHead</option><option>PreferBranch</option><option>PreferAgent</option></select></label>
    {strategy === "PreferAgent" && <label className="field">Agent priority <small>Comma-separated, highest priority first</small><input value={priority} onChange={(e) => setPriority(e.target.value)} placeholder="agent-backend, agent-frontend" /></label>}
    <label className="field">Decision rationale<textarea rows={3} value={rationale} onChange={(e) => setRationale(e.target.value)} placeholder="Explain why this resolution is appropriate." /></label>
    <div className="notice warn"><div className="grow"><strong>Review required</strong>The resolver applies a deterministic policy. It cannot determine whether the result is semantically correct.</div></div>
  </Modal>;
}

export function DiffModal({ branch, onClose }: { branch: Branch; onClose: () => void }) {
  const [diff, setDiff] = useState<BranchDiff | null>(null); const [error, setError] = useState("");
  useEffect(() => { api<BranchDiff>(`/branches/${branch.id}/diff`).then(setDiff).catch((e) => setError(e instanceof Error ? e.message : "Could not load diff")); }, [branch.id]);
  return <Modal size="xl" title={`Changes in ${branch.name}`} description="Proposed values compared with the base snapshot and the current HEAD." onClose={onClose} footer={<button className="btn btn-secondary" onClick={onClose}>Close</button>}>
    {error ? <div className="notice err" role="alert"><div className="grow"><strong>Diff unavailable</strong>{error}</div></div>
      : !diff ? <div className="stack" aria-busy="true"><Skeleton h={96} /><Skeleton h={96} /></div>
      : diff.changes.length === 0 ? <Empty title="No changes yet">Write a value to this branch to see it here.</Empty>
      : diff.changes.map((c) => <div className="stack" key={c.key}>
        <div className="row between"><strong className="data">{c.key}</strong>{c.head_changed_since_base ? <Tag tone="warn">HEAD changed since base</Tag> : <Tag tone="ok">Clean</Tag>}</div>
        {c.intent && <span className="muted">Intent: {c.intent}</span>}
        <ThreeWay items={[{ label: "Base", value: c.base, present: c.base_present }, { label: "HEAD", value: c.head, present: c.head_present }, { label: "Proposed", value: c.proposed, present: c.proposed_present }]} />
      </div>)}
  </Modal>;
}

export function EventInspector({ events, index, setIndex, onClose }: { events: EventItem[]; index: number; setIndex: (i: number) => void; onClose: () => void }) {
  const event = events[index];
  return <Modal drawer title="Event inspector" description="Step through recorded coordination events." onClose={onClose}>
    {!event ? <Empty title="No events recorded" /> : <>
      <input type="range" min={0} max={Math.max(0, events.length - 1)} value={index} onChange={(e) => setIndex(Number(e.target.value))} aria-label="Event position" />
      <div className="row between muted"><span className="data">Event {index + 1} / {events.length}</span><span>{clock(event.timestamp)} · {timeAgo(event.timestamp)}</span></div>
      <div className="row"><button className="btn btn-secondary" disabled={index <= 0} onClick={() => setIndex(index - 1)}>Previous</button><button className="btn btn-secondary" disabled={index >= events.length - 1} onClick={() => setIndex(index + 1)}>Next</button></div>
      <Json value={event} /></>}
  </Modal>;
}

/* ---------- Update Plan ---------- */
const LOCAL_PLANS: Plan[] = [
  { id: "pro", name: "Pro", description: "For individuals and small projects coordinating a few agents." },
  { id: "team", name: "Team", description: "For teams that share a workspace and review conflicts together." },
  { id: "enterprise", name: "Enterprise", description: "For organizations that need security controls and support." },
];
export function PlansModal({ onClose }: { onClose: () => void }) {
  const toast = useToast();
  const remote = useOptional<PlansResponse>("/billing/plans");
  const plans = remote.status === "ready" && remote.data?.plans?.length ? remote.data.plans : LOCAL_PLANS;
  const current = remote.data?.current || null;
  const choose = async (plan: Plan) => {
    if (plan.id === "enterprise" && PLANS_URL) { window.open(PLANS_URL, "_blank", "noopener"); return; }
    try { const r = await api<{ url: string }>("/billing/checkout", { method: "POST", body: JSON.stringify({ plan: plan.id }) }); window.location.href = r.url; }
    catch (e) { toast(isUnavailable(e) ? "Billing endpoint is not available on this API yet." : e instanceof Error ? e.message : "Checkout failed", "err"); }
  };
  return <Modal size="xl" title="Update plan" description="Compare the available plans." onClose={onClose}>
    {remote.status === "loading" ? <div className="plans" aria-busy="true"><Skeleton h={200} /><Skeleton h={200} /><Skeleton h={200} /></div> :
      <div className="plans">{plans.map((p) => <div key={p.id} className={`plan ${current === p.id ? "current" : ""}`}>
        <div className="row between"><h3>{p.name}</h3>{current === p.id && <Tag tone="accent">Current</Tag>}</div>
        <p className="muted">{p.description}</p>
        <div className="price">{p.price || "—"}{p.price && p.period ? <small className="muted" style={{ fontSize: 13 }}> / {p.period}</small> : null}</div>
        {p.features?.length ? <ul>{p.features.map((f) => <li key={f}>{f}</li>)}</ul> : null}
        <div style={{ marginTop: "auto", paddingTop: 16 }}><button className={`btn btn-block ${p.id === "pro" ? "btn-primary" : "btn-secondary"}`} disabled={current === p.id} onClick={() => void choose(p)}>{p.cta || (p.id === "enterprise" ? "Contact sales" : `Choose ${p.name}`)}</button></div>
      </div>)}</div>}
    {remote.status === "unavailable" && <p className="muted">Pricing and plan details are not provided by this API yet (<code>GET /api/billing/plans</code>).</p>}
  </Modal>;
}

/* ---------- Cerbère AG summary ---------- */
export function CerbereDrawer({ onClose }: { onClose: () => void }) {
  const [window_, setWindow] = useState<"24h" | "7d" | "30d">("24h");
  const [filter, setFilter] = useState<"all" | "blocked" | "flagged" | "allowed">("all");
  const s = useOptional<CerbereSummary>(`/cerbere/summary?window=${window_}`);
  const items = (s.data?.items || []).filter((i) => filter === "all" || i.decision === filter);
  const tone = (d: string) => (d === "blocked" ? "err" : d === "flagged" ? "warn" : "ok") as "err" | "warn" | "ok";
  const totals = s.data?.totals;
  return <Modal drawer title="Cerbère AG" description="What Cerbère AG blocked, flagged or let through." onClose={onClose}>
    <div className="row between"><div className="row"><img src={cerbereIcon} width={32} height={32} alt="" style={{ borderRadius: 6 }} /><strong>Security summary</strong></div>
      <Seg label="Time window" value={window_} onChange={setWindow} options={[{ id: "24h", label: "24h" }, { id: "7d", label: "7d" }, { id: "30d", label: "30d" }]} /></div>
    {s.status === "loading" && <div className="stack" aria-busy="true"><Skeleton h={72} /><Skeleton h={160} /></div>}
    {s.status === "unavailable" && <Empty icon={<Shield size={20} />} title="Cerbère AG is not connected">Expose <code>GET /api/cerbere/summary</code> on the Cohort API to show blocked, flagged and allowed actions here.</Empty>}
    {s.status === "error" && <div className="notice err" role="alert"><div className="grow"><strong>Could not load the summary</strong>{s.error}</div><button className="btn btn-secondary" onClick={s.reload}>Retry</button></div>}
    {s.status === "ready" && totals && <>
      <div className="three">{(["blocked", "flagged", "allowed"] as const).map((k) => <div className="card metric" key={k} style={{ padding: 16 }}><span style={{ textTransform: "capitalize" }}>{k}</span><strong className="data" style={{ fontSize: 24, color: k === "blocked" ? "var(--err)" : k === "flagged" ? "var(--warn)" : "var(--ok)" }}>{totals[k].toLocaleString()}</strong></div>)}</div>
      <Seg label="Decision filter" value={filter} onChange={setFilter} options={[{ id: "all", label: "All" }, { id: "blocked", label: "Blocked" }, { id: "flagged", label: "Flagged" }, { id: "allowed", label: "Allowed" }]} />
      {items.length === 0 ? <Empty title="Nothing to show">No {filter === "all" ? "" : filter + " "}decisions in this window.</Empty> :
        <div className="card" style={{ overflow: "hidden" }}>{items.map((i) => <div className="list-row" key={i.id} style={{ alignItems: "flex-start" }}>
          <div className="grow"><strong>{i.rule}</strong><small>{i.agent_id} · <span className="data">{i.target}</span></small><small>{i.reason}</small></div>
          <div style={{ textAlign: "right" }}><Tag tone={tone(i.decision)}>{i.decision}</Tag><small className="data" style={{ display: "block", marginTop: 4 }}>{clock(i.timestamp)}</small></div></div>)}</div>}
      {s.data?.by_rule?.length ? <div className="stack"><strong>Top rules</strong>{s.data.by_rule.slice(0, 5).map((r) => <div className="row between" key={r.rule}><span>{r.rule}</span><span className="data">{r.count.toLocaleString()}</span></div>)}</div> : null}
    </>}
  </Modal>;
}
