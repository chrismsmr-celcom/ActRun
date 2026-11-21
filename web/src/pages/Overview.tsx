import { useMemo } from "react";
import { Check, GitBranch, Plus } from "lucide-react";
import { Card, Disconnected, Empty, Metric, PageHead, Skeleton, TableSkeleton } from "../components/ui";
import { eventTone, short, timeAgo } from "../lib/format";
import type { Ctx } from "./ctx";

export default function Overview({ ctx }: { ctx: Ctx }) {
  const { data } = ctx; const { overview, branches, events, leases, state } = data;
  const first = !data.loaded;
  const open = branches.filter((b) => b.status === "open");
  const conflicts = open.filter((b) => b.conflicting_keys.length > 0);
  const days = useMemo(() => {
    const out = Array.from({ length: 14 }, (_, i) => { const d = new Date(); d.setDate(d.getDate() - (13 - i)); d.setHours(0, 0, 0, 0); return { label: String(d.getDate()), key: d.toDateString(), commits: 0, conflicts: 0 }; });
    events.forEach((e) => { const day = out.find((d) => d.key === new Date(e.timestamp).toDateString()); if (!day) return;
      if (/conflict/.test(e.action)) day.conflicts++; else if (/commit|resolve/.test(e.action) && !/abort/.test(e.action)) day.commits++; });
    return out;
  }, [events]);
  const max = Math.max(1, ...days.map((d) => Math.max(d.commits, d.conflicts)));
  const attempts = (overview?.commit_count ?? 0) + (overview?.conflict_count ?? 0);
  const rate = attempts ? `${((overview!.conflict_count / attempts) * 100).toFixed(1)}%` : "—";
  return <div className="page">
    <PageHead title="Workspace overview" description="See how your agents coordinate, share state and resolve competing changes."
      actions={<button className="btn btn-primary" onClick={ctx.openCreate}><Plus size={16} />New branch</button>} />
    {data.error && <Disconnected message={data.error} onRetry={ctx.refresh} />}
    <div className="grid">
      {first ? [0, 1, 2, 3].map((i) => <div key={i} className="card metric c3"><Skeleton w={96} h={14} /><div style={{ height: 8 }} /><Skeleton w={64} h={32} /></div>) : <>
        <Metric label="Open branches" value={open.length} hint={`${state.items.length} shared keys`} />
        <Metric label="Unresolved conflicts" value={conflicts.length} tone={conflicts.length ? "err" : undefined} hint={`Conflict rate ${rate}`} />
        <Metric label="Active leases" value={leases.length} hint={`HEAD ${short(state.head)}`} />
        <Metric label="Recorded events" value={(overview?.event_count ?? events.length).toLocaleString()} hint={`${overview?.snapshot_count ?? 0} snapshots`} /></>}
      <Card className="c8" title="Coordination activity" description="Commits and conflict events · last 14 days">
        {first ? <TableSkeleton rows={3} /> : <>
          <div className="legend"><span><i style={{ background: "var(--accent)" }} />Commits</span><span><i style={{ background: "var(--err)" }} />Conflicts</span></div>
          <div className="chart" role="img" aria-label="Commits and conflicts per day, last 14 days">
            <div className="axis"><span>{max}</span><span>0</span></div>
            <div className="cols">{days.map((d, i) => <div className="day" key={d.key}><div className="bars">
              <i style={{ height: `${(d.commits / max) * 100}%` }} title={`${d.commits} commits`} /><i className="c" style={{ height: `${(d.conflicts / max) * 100}%` }} title={`${d.conflicts} conflicts`} /></div>
              <small>{i % 2 === 0 ? d.label : ""}</small></div>)}</div>
          </div></>}
      </Card>
      <Card className="c4" title="Needs attention" description="Conflicts that require a decision" actions={conflicts.length ? <span className="tag err"><i />{conflicts.length}</span> : undefined}>
        {first ? <TableSkeleton rows={2} /> : conflicts.length === 0 ? <Empty icon={<Check size={20} />} title="No conflicts to resolve">Branches are clear to merge.</Empty> :
          conflicts.slice(0, 4).map((b) => <div className="list-row" key={b.id}><div className="grow"><strong>{b.name}</strong><small>{b.agent_id} · {b.conflicting_keys.length} conflicting key(s)</small></div>
            <button className="btn btn-secondary" onClick={() => ctx.openResolve(b)}>Review</button></div>)}
      </Card>
      <Card className="c12" title="Recent activity" description="Latest events recorded by the coordination runtime" actions={<button className="btn btn-secondary" onClick={() => ctx.go("events")}>Open event log</button>}>
        {first ? <TableSkeleton /> : events.length === 0 ? <Empty icon={<GitBranch size={20} />} title="No activity recorded yet" action={<button className="btn btn-primary" onClick={ctx.openCreate}>Create a branch</button>}>Create a branch, write a value and merge it to see your first coordination events.</Empty> :
          <div className="tbl-wrap"><table><thead><tr><th>Event</th><th>Agent</th><th>Event ID</th><th className="num">Time</th></tr></thead><tbody>
            {events.slice(0, 6).map((e) => <tr key={e.event_id}><td><span className={`dot ${eventTone(e.action)}`} />{e.action}</td><td>{e.agent_id}</td><td><code>{short(e.event_id)}</code></td><td className="num">{timeAgo(e.timestamp)}</td></tr>)}</tbody></table></div>}
      </Card>
    </div>
  </div>;
}
