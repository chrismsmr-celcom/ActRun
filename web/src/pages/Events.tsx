import { useEffect, useState } from "react";
import { Download, ScrollText } from "lucide-react";
import { Card, Disconnected, Empty, PageHead, SearchInput, TableSkeleton } from "../components/ui";
import { download, eventTone, short } from "../lib/format";
import type { Ctx } from "./ctx";

export default function Events({ ctx }: { ctx: Ctx }) {
  const { data } = ctx; const [tab, setTab] = useState<"log" | "trace">("log");
  const [filter, setFilter] = useState(ctx.query);
  const [trace, setTrace] = useState<{ actions: Record<string, number>; bad: number; total: number } | null>(null); const [text, setText] = useState("");
  useEffect(() => { if (ctx.query) { setFilter(ctx.query); ctx.clearQuery(); } }, [ctx.query]); // eslint-disable-line react-hooks/exhaustive-deps
  const rows = data.events.filter((e) => `${e.action} ${e.agent_id} ${e.event_id}`.toLowerCase().includes(filter.toLowerCase()));
  const parse = (raw: string) => {
    const actions: Record<string, number> = {}; let bad = 0; let total = 0;
    raw.split(/\r?\n/).filter((l) => l.trim()).forEach((line) => { total++; try { const a = JSON.parse(line).action || "unknown"; actions[a] = (actions[a] || 0) + 1; } catch { bad++; } });
    setTrace({ actions, bad, total });
  };
  return <div className="page">
    <PageHead title="Event log" description="An ordered record of coordination decisions, writes, leases and branch operations."
      actions={<button className="btn btn-secondary" onClick={() => download("cohort-events.jsonl", data.events.map((e) => JSON.stringify(e)).join("\n"))} disabled={!data.events.length}><Download size={16} />Export JSONL</button>} />
    {data.error && <Disconnected message={data.error} onRetry={ctx.refresh} />}
    <div className="tabs" role="tablist"><button role="tab" aria-selected={tab === "log"} onClick={() => setTab("log")}>Log</button><button role="tab" aria-selected={tab === "trace"} onClick={() => setTab("trace")}>Trace analyzer</button></div>
    {tab === "log" ? <>
      <div className="row between"><SearchInput value={filter} onChange={setFilter} placeholder="Filter by event, agent or ID" /><span className="muted data">{rows.length} of {data.events.length} events</span></div>
      <Card>{!data.loaded ? <TableSkeleton /> : <div className="tbl-wrap"><table><thead><tr><th>Event</th><th>Agent</th><th>Event ID</th><th className="num">Recorded at</th><th /></tr></thead><tbody>
        {rows.map((e) => <tr key={e.event_id}><td><span className={`dot ${eventTone(e.action)}`} />{e.action}</td><td>{e.agent_id}</td><td><code>{short(e.event_id)}</code></td>
          <td className="num">{new Date(e.timestamp).toLocaleString()}</td><td><div className="cell-actions"><button className="btn btn-link" onClick={() => ctx.openInspector(data.events.findIndex((x) => x.event_id === e.event_id))}>Inspect</button></div></td></tr>)}
        {!rows.length && <tr><td colSpan={5}><Empty icon={<ScrollText size={20} />} title={filter ? "No matching events" : "No events recorded"}>{filter ? "Try a different filter." : "Events appear as agents create branches, write values and merge."}</Empty></td></tr>}
      </tbody></table></div>}</Card></> :
      <div className="grid">
        <Card className="c5" title="Load a trace" description="Paste or open an exported JSONL event trace" flush={false}><div className="stack">
          <input type="file" accept=".jsonl,.json,.txt" aria-label="Open JSONL file" onChange={(e) => { const f = e.target.files?.[0]; if (f) void f.text().then(parse); }} />
          <label className="field">Or paste events<textarea rows={6} className="data" value={text} onChange={(e) => setText(e.target.value)} placeholder="One JSON event per line" /></label>
          <div className="row"><button className="btn btn-primary" onClick={() => parse(text)} disabled={!text.trim()}>Analyze pasted events</button>
            <button className="btn btn-secondary" onClick={() => parse(data.events.map((e) => JSON.stringify(e)).join("\n"))} disabled={!data.events.length}>Analyze loaded log</button></div></div></Card>
        <Card className="c7" title="Events by action" description={trace ? `${trace.total} lines parsed${trace.bad ? ` · ${trace.bad} invalid` : ""}` : "Results appear here"}>
          {!trace ? <Empty title="Nothing analyzed yet">Load a trace to count events by action.</Empty> :
            <div className="tbl-wrap"><table><thead><tr><th>Action</th><th className="num">Count</th></tr></thead><tbody>{Object.entries(trace.actions).sort((a, b) => b[1] - a[1]).map(([a, c]) => <tr key={a}><td>{a}</td><td className="num">{c}</td></tr>)}</tbody></table></div>}
        </Card>
      </div>}
  </div>;
}
