import { useEffect, useState } from "react";
import { GitBranch, Plus } from "lucide-react";
import { api } from "../lib/api";
import { Card, Disconnected, Empty, PageHead, Seg, SearchInput, TableSkeleton, Tag } from "../components/ui";
import { short, timeAgo } from "../lib/format";
import type { Ctx } from "./ctx";

export default function Branches({ ctx }: { ctx: Ctx }) {
  const { data } = ctx;
  const [filter, setFilter] = useState(ctx.query); const [status, setStatus] = useState<"open" | "merged">("open"); const [selected, setSelected] = useState<string[]>([]);
  useEffect(() => { if (ctx.query) { setFilter(ctx.query); ctx.clearQuery(); } }, [ctx.query]); // eslint-disable-line react-hooks/exhaustive-deps
  const open = data.branches.filter((b) => b.status === "open");
  const visible = data.branches.filter((b) => b.status === status && `${b.name} ${b.agent_id}`.toLowerCase().includes(filter.toLowerCase()));
  const selectable = visible.filter((b) => b.status === "open" && b.conflicting_keys.length === 0);
  const merge = (id: string) => api<{ conflict?: boolean; conflicting_keys?: string[] }>(`/branches/${id}/commit`, { method: "POST" }).then((r) => { if (r.conflict) throw new Error(`Merge blocked. Conflicting keys: ${(r.conflicting_keys || []).join(", ")}`); });
  return <div className="page">
    <PageHead title="Branches" description="Isolated workspaces where agents change state without overwriting one another." actions={<button className="btn btn-primary" onClick={ctx.openCreate}><Plus size={16} />Create branch</button>} />
    {data.error && <Disconnected message={data.error} onRetry={ctx.refresh} />}
    <div className="row between"><div className="row" style={{ flex: 1 }}><SearchInput value={filter} onChange={setFilter} placeholder="Search branches or agents" />
      <Seg label="Branch status" value={status} onChange={(s) => { setStatus(s); setSelected([]); }} options={[{ id: "open", label: `Open ${open.length}` }, { id: "merged", label: "Merged" }]} /></div>
      <button className="btn btn-secondary" disabled={!selected.length || ctx.busy} onClick={() => void ctx.run(async () => { for (const id of selected) await merge(id); setSelected([]); }, "Selected branches merged")}>Merge selected ({selected.length})</button></div>
    <Card>{!data.loaded ? <TableSkeleton /> : <div className="tbl-wrap"><table><thead><tr>
      <th style={{ width: 40 }}><input type="checkbox" aria-label="Select all mergeable branches" disabled={!selectable.length} checked={selectable.length > 0 && selectable.every((b) => selected.includes(b.id))} onChange={(e) => setSelected(e.target.checked ? selectable.map((b) => b.id) : [])} /></th>
      <th>Branch</th><th>Owner</th><th>Base version</th><th>Status</th><th className="num">Created</th><th /></tr></thead><tbody>
      {visible.map((b) => { const conflict = b.conflicting_keys.length > 0; return <tr key={b.id}>
        <td><input type="checkbox" aria-label={`Select ${b.name}`} disabled={b.status !== "open" || conflict} checked={selected.includes(b.id)} onChange={(e) => setSelected((p) => e.target.checked ? [...p, b.id] : p.filter((x) => x !== b.id))} /></td>
        <td><strong>{b.name}</strong><small className="data">{b.id.slice(0, 8)}</small></td><td>{b.agent_id}</td><td><code>{short(b.base_version)}</code></td>
        <td>{b.status === "merged" ? <Tag tone="ok">Merged</Tag> : conflict ? <Tag tone="err">Conflict</Tag> : <Tag>Open</Tag>}</td><td className="num">{timeAgo(b.created_at)}</td>
        <td>{b.status === "open" ? <div className="cell-actions">
          <button className="btn-link btn" onClick={() => ctx.openDiff(b)}>Changes</button>
          <button className="btn-link btn" disabled={ctx.busy} onClick={() => ctx.openWrite(b)}>Write</button>
          {conflict ? <button className="btn-link btn" onClick={() => ctx.openResolve(b)}>Resolve</button> : <button className="btn-link btn" disabled={ctx.busy} onClick={() => void ctx.run(() => merge(b.id), "Branch merged")}>Merge</button>}</div> : null}</td></tr>; })}
      {!visible.length && <tr><td colSpan={7}><Empty icon={<GitBranch size={20} />} title="No branches found" action={<button className="btn btn-primary" onClick={ctx.openCreate}>Create branch</button>}>Create a branch to give an agent an isolated place to work.</Empty></td></tr>}
    </tbody></table></div>}</Card>
  </div>;
}
