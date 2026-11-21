import { Fragment, useEffect, useState } from "react";
import { Copy, Database } from "lucide-react";
import { Card, Disconnected, Empty, PageHead, SearchInput, TableSkeleton, Json, useToast } from "../components/ui";
import { short } from "../lib/format";
import type { Ctx } from "./ctx";

export default function State({ ctx }: { ctx: Ctx }) {
  const { data } = ctx; const toast = useToast();
  const [filter, setFilter] = useState(ctx.query); const [open, setOpen] = useState<string | null>(null);
  useEffect(() => { if (ctx.query) { setFilter(ctx.query); ctx.clearQuery(); } }, [ctx.query]); // eslint-disable-line react-hooks/exhaustive-deps
  const items = data.state.items.filter((i) => i.key.toLowerCase().includes(filter.toLowerCase()));
  const copy = (text: string) => { void navigator.clipboard?.writeText(text).then(() => toast("Copied to clipboard"), () => toast("Copy failed", "err")); };
  return <div className="page">
    <PageHead title="Shared state" description="A content-addressed view of the values your agents read and write together." actions={<span className="tag accent"><i />HEAD <span className="data">{short(data.state.head)}</span></span>} />
    {data.error && <Disconnected message={data.error} onRetry={ctx.refresh} />}
    <SearchInput value={filter} onChange={setFilter} placeholder="Filter keys" />
    <Card title="Workspace keys" description={`${data.state.items.length} keys in the current snapshot`}>
      {!data.loaded ? <TableSkeleton /> : <div className="tbl-wrap"><table><thead><tr><th>Key</th><th>Value hash</th><th>Value preview</th><th /></tr></thead><tbody>
        {items.map((i) => { const text = JSON.stringify(i.value); const expanded = open === i.key; return <Fragment key={i.key}>
          <tr onClick={() => setOpen(expanded ? null : i.key)} style={{ cursor: "pointer" }}>
            <td><strong className="data">{i.key}</strong></td><td><code>{short(i.value_hash)}</code></td>
            <td className="data" style={{ maxWidth: 420, overflow: "hidden", textOverflow: "ellipsis" }}>{text}</td>
            <td><div className="cell-actions"><button className="icon-btn" aria-label={`Copy value of ${i.key}`} onClick={(e) => { e.stopPropagation(); copy(JSON.stringify(i.value, null, 2)); }}><Copy size={14} /></button></div></td></tr>
          {expanded && <tr><td colSpan={4}><Json value={i.value} /></td></tr>}</Fragment>; })}
        {!items.length && <tr><td colSpan={4}><Empty icon={<Database size={20} />} title={filter ? "No matching keys" : "Shared state is empty"}>{filter ? "Try a different filter." : "Create a branch, use Write to add a key, then merge it. Agents can also write through the API or the MCP server."}</Empty></td></tr>}
      </tbody></table></div>}
    </Card>
  </div>;
}
