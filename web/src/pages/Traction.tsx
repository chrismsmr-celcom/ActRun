import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";
import { organizationId, supabase } from "../auth";
import { Card, Empty, Metric, PageHead, Skeleton } from "../components/ui";

type Metrics = { self_hosted_installations_total: number; self_hosted_installations_active_30d: number; versions: { version: string; installations: number }[]; note: string };
type Traffic = { snapshots: { date: string; clones: number; unique_cloners: number }[] };

export default function Traction() {
  const [metrics, setMetrics] = useState<Metrics | null>(null); const [traffic, setTraffic] = useState<Traffic | null>(null);
  const [metricsError, setMetricsError] = useState(""); const [trafficError, setTrafficError] = useState("");
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const headers: Record<string, string> = { "X-Organization-ID": organizationId };
        if (supabase) { const { data } = await supabase.auth.getSession(); if (data.session?.access_token) headers.Authorization = "Bearer " + data.session.access_token; }
        const response = await fetch(API_BASE + "/api/traction", { headers }); const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Traction endpoint unavailable");
        if (active) setMetrics(body as Metrics);
      } catch (e) { if (active) setMetricsError(e instanceof Error ? e.message : "Traction metrics unavailable"); }
    })();
    (async () => {
      try {
        const response = await fetch("https://raw.githubusercontent.com/chrismsmr-celcom/cerbere-cohort/main/metrics/github-traffic.json");
        if (!response.ok) throw new Error("No archive yet. Configure COHORT_TRAFFIC_TOKEN and run the traffic workflow.");
        const data = (await response.json()) as Traffic; if (active) setTraffic(data);
      } catch (e) { if (active) setTrafficError(e instanceof Error ? e.message : "GitHub traffic archive unavailable"); }
    })();
    return () => { active = false; };
  }, []);
  const latest = traffic?.snapshots?.[traffic.snapshots.length - 1];
  const v = (n: number | undefined) => (n === undefined ? "—" : n.toLocaleString());
  return <div className="page">
    <PageHead title="Traction" description="Repository interest and voluntary self-hosted installation activity. These are not customer counts." />
    <div className="grid">
      <Metric label="Self-hosted installations" value={v(metrics?.self_hosted_installations_total)} /><Metric label="Active installations · 30d" value={v(metrics?.self_hosted_installations_active_30d)} />
      <Metric label="GitHub clones · latest 14d" value={v(latest?.clones)} /><Metric label="Unique cloners · latest 14d" value={v(latest?.unique_cloners)} />
      <Card className="c6" title="Self-hosted adoption" description="Opt-in installation heartbeats">
        {metricsError ? <Empty title="Telemetry unavailable">{metricsError}. Enable COHORT_TELEMETRY_COLLECTOR_ENABLED on the hosted API.</Empty> : !metrics ? <div className="stack" style={{ padding: "0 24px 24px" }}><Skeleton h={32} /></div> :
          <>{metrics.versions.map((x) => <div className="kv" key={x.version}><span>Version {x.version}</span><span className="data">{x.installations}</span></div>)}<div className="kv"><span>Note</span><span style={{ textAlign: "right" }}>{metrics.note}</span></div></>}
      </Card>
      <Card className="c6" title="GitHub repository traffic" description="Archived rolling 14-day totals">
        {trafficError ? <Empty title="Archive not available">{trafficError}</Empty> : !traffic?.snapshots?.length ? <div className="stack" style={{ padding: "0 24px 24px" }}><Skeleton h={32} /></div> :
          <div className="tbl-wrap"><table><thead><tr><th>Snapshot</th><th className="num">Clones · 14d</th><th className="num">Unique cloners · 14d</th></tr></thead><tbody>{traffic.snapshots.slice(-14).reverse().map((r) => <tr key={r.date}><td>{r.date}</td><td className="num">{r.clones}</td><td className="num">{r.unique_cloners}</td></tr>)}</tbody></table></div>}
      </Card>
    </div>
  </div>;
}
