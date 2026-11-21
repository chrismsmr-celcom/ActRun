import { useMemo } from "react";
import { AlertTriangle, CheckCircle2, Info, Lightbulb, OctagonAlert } from "lucide-react";
import { API_BASE } from "../lib/api";
import { Card, Disconnected, Empty, PageHead, Skeleton, Tag } from "../components/ui";
import { countdown } from "../lib/format";
import { useOptional } from "../lib/useCohort";
import type { AdvisorItem, Data, Tab } from "../lib/types";
import type { Ctx } from "./ctx";

/** Rules computed from live API data. Nothing here is invented: every item cites numbers from your workspace. */
export function localInsights(data: Data): AdvisorItem[] {
  const out: AdvisorItem[] = []; const add = (i: Omit<AdvisorItem, "source">) => out.push({ ...i, source: "local" });
  if (!data.connected && data.loaded) { add({ id: "offline", severity: "critical", title: "The Cohort API is unreachable", detail: data.error || "No response from the runtime.", action: { label: "Open Performance", tab: "performance" } }); return out; }
  if (!data.loaded) return out;
  const open = data.branches.filter((b) => b.status === "open");
  const conflicts = open.filter((b) => b.conflicting_keys.length > 0);
  if (conflicts.length) add({ id: "conflicts", severity: "warning", title: `${conflicts.length} branch${conflicts.length > 1 ? "es have" : " has"} unresolved conflicts`, detail: `Blocked: ${conflicts.slice(0, 3).map((b) => b.name).join(", ")}. Agents keep working on stale state until a decision is recorded.`, action: { label: "Review branches", tab: "branches" } });
  const stale = open.filter((b) => Date.now() - new Date(b.created_at).getTime() > 24 * 3600e3);
  if (stale.length) add({ id: "stale", severity: "info", title: `${stale.length} open branch${stale.length > 1 ? "es are" : " is"} older than 24 hours`, detail: "Long-lived branches drift from HEAD and are more likely to conflict. Merge or discard them.", action: { label: "Open branches", tab: "branches" } });
  const o = data.overview; const attempts = (o?.commit_count ?? 0) + (o?.conflict_count ?? 0);
  if (o && attempts >= 10 && o.conflict_count / attempts > 0.1) add({ id: "rate", severity: "warning", title: `Conflict rate is ${((o.conflict_count / attempts) * 100).toFixed(1)}%`, detail: "More than one commit attempt in ten collides. Consider splitting keys between agents or requiring leases for shared keys.", action: { label: "Open Leases", tab: "leases" } });
  if (data.settings && !data.settings.require_leases && (conflicts.length > 0 || (o?.conflict_count ?? 0) > 0)) add({ id: "leases", severity: "info", title: "Leases are advisory", detail: "Conflicts have occurred while lease enforcement is off. Enabling it makes writes require a lease on the key (COHORT_REQUIRE_LEASES).", action: { label: "Open Setting", tab: "settings" } });
  const soon = data.leases.filter((l) => l.expires_at - Date.now() / 1000 < 15);
  if (soon.length) add({ id: "expiring", severity: "info", title: `${soon.length} lease${soon.length > 1 ? "s expire" : " expires"} within 15 seconds`, detail: soon.slice(0, 3).map((l) => `${l.key} (${l.agent_id}, ${countdown(l.expires_at, Date.now())})`).join(" · "), action: { label: "Open Leases", tab: "leases" } });
  const remote = Boolean(API_BASE) && !/localhost|127\.0\.0\.1/.test(API_BASE);
  if (remote && data.settings?.authentication === "development-bypass") add({ id: "auth", severity: "critical", title: "Authentication is disabled on a remote API", detail: "The API reports a development bypass while serving a non-local origin. Configure Supabase authentication before exposing it.", action: { label: "Open Setting", tab: "settings" } });
  if (data.events.length === 0) add({ id: "empty", severity: "info", title: "No agent has written to this workspace yet", detail: "Connect an agent through the Gateway to start recording coordination events.", action: { label: "Open Gateway", tab: "gateway" } });
  return out;
}

const icon = { critical: <OctagonAlert size={18} color="var(--err)" />, warning: <AlertTriangle size={18} color="var(--warn)" />, info: <Info size={18} color="var(--accent)" /> };
export default function Advisor({ ctx }: { ctx: Ctx }) {
  const { data } = ctx;
  const server = useOptional<{ items: Omit<AdvisorItem, "source">[] }>("/advisor", 30000);
  const items = useMemo(() => {
    const remote: AdvisorItem[] = (server.data?.items || []).map((i) => ({ ...i, source: "server" as const }));
    const order = { critical: 0, warning: 1, info: 2 };
    return [...localInsights(data), ...remote].sort((a, b) => order[a.severity] - order[b.severity]);
  }, [data, server.data]);
  const act = (i: AdvisorItem) => { if (i.action?.href) window.open(i.action.href, "_blank", "noopener"); else if (i.action?.tab) ctx.go(i.action.tab as Tab); };
  return <div className="page">
    <PageHead title="Advisor" description="Recommendations drawn from how your agents are actually coordinating." />
    {data.error && <Disconnected message={data.error} onRetry={ctx.refresh} />}
    <Card title="Recommendations" description={server.status === "ready" ? "From your workspace and the Advisor service" : "From your workspace"} actions={items.length ? <Tag tone={items.some((i) => i.severity !== "info") ? "warn" : "accent"}>{items.length}</Tag> : undefined}>
      {!data.loaded ? <div className="stack" style={{ padding: "0 24px 24px" }}><Skeleton h={48} /><Skeleton h={48} /></div> : items.length === 0 ?
        <Empty icon={<CheckCircle2 size={20} />} title="Nothing to recommend">Coordination looks healthy. New suggestions appear here as your workspace changes.</Empty> :
        items.map((i) => <div className="list-row" key={`${i.source}-${i.id}`} style={{ alignItems: "flex-start" }}>
          <span style={{ paddingTop: 2 }}>{icon[i.severity]}</span>
          <div className="grow"><strong>{i.title}</strong><small style={{ fontSize: 13 }}>{i.detail}</small></div>
          {i.action && <button className="btn btn-secondary" onClick={() => act(i)}>{i.action.label}</button>}</div>)}
    </Card>
    {server.status === "unavailable" && <p className="muted"><Lightbulb size={14} style={{ verticalAlign: -2 }} /> Add <code>GET /api/advisor</code> to merge server-generated recommendations into this list.</p>}
  </div>;
}
