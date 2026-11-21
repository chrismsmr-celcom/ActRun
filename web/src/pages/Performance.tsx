import { useEffect, useMemo, useState } from "react";
import { Gauge } from "lucide-react";
import { getSamples, subscribeSamples } from "../lib/api";
import type { Sample } from "../lib/api";
import { Card, Disconnected, Empty, Metric, PageHead, Skeleton, Tag } from "../components/ui";
import { clock, ms, pct, percentile } from "../lib/format";
import { useOptional } from "../lib/useCohort";
import type { PerformanceReport } from "../lib/types";
import type { Ctx } from "./ctx";

function useSamples() {
  const [list, setList] = useState<Sample[]>(() => [...getSamples()]);
  useEffect(() => subscribeSamples(() => setList([...getSamples()])), []);
  return list;
}
function Spark({ values, height = 120, label }: { values: number[]; height?: number; label: string }) {
  if (values.length < 2) return <Empty title="Collecting samples">The chart fills in as the dashboard polls the API.</Empty>;
  const w = 600; const max = Math.max(1, ...values) * 1.15; const step = w / (values.length - 1);
  const pts = values.map((v, i) => `${(i * step).toFixed(1)},${(height - (v / max) * (height - 8) - 4).toFixed(1)}`).join(" ");
  return <div style={{ padding: "0 24px 24px" }}><svg className="spark" viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" role="img" aria-label={label}>
    <polyline points={`0,${height} ${pts} ${w},${height}`} fill="var(--accent-soft)" stroke="none" /><polyline points={pts} fill="none" stroke="var(--accent)" strokeWidth="2" vectorEffect="non-scaling-stroke" /></svg>
    <div className="row between muted data" style={{ fontSize: 12 }}><span>oldest</span><span>peak {ms(Math.max(...values))}</span><span>latest</span></div></div>;
}

export default function Performance({ ctx }: { ctx: Ctx }) {
  const { data } = ctx; const samples = useSamples();
  const server = useOptional<PerformanceReport>("/performance", 15000);
  const recent = samples.slice(-120);
  const stats = useMemo(() => {
    const byPath = new Map<string, Sample[]>(); recent.forEach((s) => { const l = byPath.get(s.path) || []; l.push(s); byPath.set(s.path, l); });
    const endpoints = [...byPath.entries()].map(([path, list]) => { const t = list.map((s) => s.ms); return { path, count: list.length, p50: percentile(t, 50), p95: percentile(t, 95), errors: list.filter((s) => !s.ok).length / list.length }; }).sort((a, b) => b.p95 - a.p95);
    const all = recent.map((s) => s.ms);
    return { endpoints, p50: percentile(all, 50), p95: percentile(all, 95), success: recent.length ? recent.filter((s) => s.ok).length / recent.length : NaN };
  }, [recent.length, samples.length]); // eslint-disable-line react-hooks/exhaustive-deps
  const throughput = data.events.filter((e) => Date.now() - new Date(e.timestamp).getTime() < 15 * 60e3).length / 15;
  const slow = stats.endpoints.filter((e) => e.count >= 3 && (e.p95 > 1000 || e.errors > 0));
  return <div className="page">
    <PageHead title="Performance" description="Speed and connection health between this dashboard, the Cohort API and your agents." />
    {data.error && <Disconnected message={data.error} onRetry={ctx.refresh} />}
    {slow.length > 0 && <div className="notice warn" role="alert"><div className="grow"><strong>Slowdown detected</strong>{slow.slice(0, 3).map((e) => `${e.path} (p95 ${ms(e.p95)}${e.errors ? `, ${pct(e.errors)} errors` : ""})`).join(" · ")}</div></div>}
    <div className="grid">
      {!data.loaded ? [0, 1, 2, 3].map((i) => <div key={i} className="card metric c3"><Skeleton w={96} h={14} /><div style={{ height: 8 }} /><Skeleton w={64} h={32} /></div> ) : <>
        <Metric label="Median latency" value={ms(stats.p50)} hint="Measured from this browser" />
        <Metric label="p95 latency" value={ms(stats.p95)} hint={`${recent.length} recent requests`} />
        <Metric label="Request success" value={pct(stats.success)} tone={stats.success < 1 ? "err" : undefined} hint="Last 120 requests" />
        <Metric label="Events per minute" value={throughput.toFixed(1)} hint="Averaged over 15 minutes" /></>}
      <Card className="c8" title="API response time" description="Latency of each request this dashboard made"><Spark values={recent.map((s) => s.ms)} label="API response time over recent requests" /></Card>
      <Card className="c4" title="Connection" description="Reported by /api/health">
        {data.health ? <><div className="kv"><span>Status</span><Tag tone={data.health.ok ? "ok" : "err"}>{data.health.ok ? "Healthy" : "Degraded"}</Tag></div>
          <div className="kv"><span>Runtime</span><span className="data">{data.health.runtime}</span></div><div className="kv"><span>Persistence</span><span className="data">{data.health.persistence}</span></div>
          <div className="kv"><span>Last refresh</span><span className="data">{data.lastUpdated ? clock(data.lastUpdated) : "—"}</span></div></> : <Empty title="No health data">The API has not answered yet.</Empty>}
      </Card>
      <Card className="c12" title="Endpoints" description="Slowest first · measured from this browser">
        <div className="tbl-wrap"><table><thead><tr><th>Endpoint</th><th className="num">Requests</th><th className="num">p50</th><th className="num">p95</th><th className="num">Errors</th></tr></thead><tbody>
          {stats.endpoints.map((e) => <tr key={e.path}><td><code>{e.path}</code></td><td className="num">{e.count}</td><td className="num">{ms(e.p50)}</td><td className="num">{e.p95 > 1000 ? <Tag tone="warn">{ms(e.p95)}</Tag> : ms(e.p95)}</td><td className="num">{pct(e.errors)}</td></tr>)}
          {!stats.endpoints.length && <tr><td colSpan={5}><Empty icon={<Gauge size={20} />} title="No requests measured yet" /></td></tr>}
        </tbody></table></div>
      </Card>
      <Card className="c12" title="Server-side metrics" description="Latency, error rate and incidents measured by the API itself"
        actions={server.status === "ready" ? <Tag tone="ok">Connected</Tag> : server.status === "unavailable" ? <Tag>Not connected</Tag> : undefined}>
        {server.status === "loading" ? <div className="stack" style={{ padding: "0 24px 24px" }}><Skeleton h={64} /></div> :
         server.status === "unavailable" ? <Empty title="Server metrics are not exposed yet">Implement <code>GET /api/performance</code> to chart server-side percentiles, per-agent latency and incidents here.</Empty> :
         server.status === "error" ? <Empty title="Could not load server metrics">{server.error}</Empty> : server.data && <>
          <div className="grid" style={{ padding: "0 24px 24px" }}>
            <div className="c3 stack"><span className="muted">p50 / p95 / p99</span><strong className="data" style={{ fontSize: 20 }}>{ms(server.data.api.p50_ms)} / {ms(server.data.api.p95_ms)} / {ms(server.data.api.p99_ms)}</strong></div>
            <div className="c3 stack"><span className="muted">Error rate</span><strong className="data" style={{ fontSize: 20 }}>{pct(server.data.api.error_rate)}</strong></div>
            <div className="c3 stack"><span className="muted">Requests per minute</span><strong className="data" style={{ fontSize: 20 }}>{server.data.api.requests_per_min.toLocaleString()}</strong></div>
          </div>
          <Spark values={server.data.series.map((s) => s.p95_ms)} label="Server p95 latency" />
          {server.data.agents.length > 0 && <div className="tbl-wrap"><table><thead><tr><th>Agent</th><th>Status</th><th className="num">Latency</th></tr></thead><tbody>{server.data.agents.map((a) => <tr key={a.agent_id}><td>{a.agent_id}</td><td><Tag tone={a.status === "ok" ? "ok" : a.status === "slow" ? "warn" : "err"}>{a.status}</Tag></td><td className="num">{ms(a.latency_ms)}</td></tr>)}</tbody></table></div>}
          {server.data.incidents.length > 0 && server.data.incidents.map((i) => <div className="list-row" key={i.id}><div className="grow"><strong>{i.title}</strong><small>{new Date(i.started_at).toLocaleString()}</small></div><Tag tone={i.resolved_at ? "ok" : i.severity === "critical" ? "err" : "warn"}>{i.resolved_at ? "Resolved" : "Ongoing"}</Tag></div>)}</>}
      </Card>
    </div>
  </div>;
}
