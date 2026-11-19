import { useEffect, useState } from "react";
import { organizationId, supabase } from "./auth";

const API = (import.meta as any).env?.VITE_API_BASE_URL || (import.meta as any).env?.VITE_API_URL || "";
type Metrics = {
  self_hosted_installations_total: number;
  self_hosted_installations_active_30d: number;
  versions: { version: string; installations: number }[];
  note: string;
};
type Traffic = {
  snapshots: { date: string; clones: number; unique_cloners: number }[];
};

export default function TractionPanel() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [traffic, setTraffic] = useState<Traffic | null>(null);
  const [metricsError, setMetricsError] = useState("");
  const [trafficError, setTrafficError] = useState("");

  useEffect(() => {
    let active = true;
    async function loadMetrics() {
      try {
        const headers: Record<string, string> = { "X-Organization-ID": organizationId };
        if (supabase) {
          const { data } = await supabase.auth.getSession();
          if (data.session?.access_token) headers.Authorization = "Bearer " + data.session.access_token;
        }
        const response = await fetch(API + "/api/traction", { headers });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Traction endpoint unavailable");
        if (active) setMetrics(body as Metrics);
      } catch (error) {
        if (active) setMetricsError(error instanceof Error ? error.message : "Traction metrics unavailable");
      }
    }
    async function loadTraffic() {
      try {
        const response = await fetch("https://raw.githubusercontent.com/chrismsmr-celcom/cerbere-cohort/main/metrics/github-traffic.json");
        if (!response.ok) throw new Error("No archive yet. Configure COHORT_TRAFFIC_TOKEN and run the traffic workflow.");
        const data = await response.json() as Traffic;
        if (active) setTraffic(data);
      } catch (error) {
        if (active) setTrafficError(error instanceof Error ? error.message : "GitHub traffic archive unavailable");
      }
    }
    void loadMetrics();
    void loadTraffic();
    return () => { active = false; };
  }, []);

  const latest = traffic?.snapshots?.[traffic.snapshots.length - 1];
  return <div>
    <div className="page-heading">
      <div><div className="eyebrow">COHORT / GROWTH</div><h1>Traction</h1><p>Repository interest and voluntary self-hosted installation activity. These are not customer counts.</p></div>
    </div>
    <section className="metric-grid">
      <div className="metric-card"><span>Self-hosted installations</span><strong>{metrics ? metrics.self_hosted_installations_total : "—"}</strong></div>
      <div className="metric-card"><span>Active installations · 30d</span><strong>{metrics ? metrics.self_hosted_installations_active_30d : "—"}</strong></div>
      <div className="metric-card"><span>GitHub clones · latest 14d</span><strong>{latest ? latest.clones : "—"}</strong></div>
      <div className="metric-card"><span>Unique cloners · latest 14d</span><strong>{latest ? latest.unique_cloners : "—"}</strong></div>
    </section>
    <div className="settings-layout">
      <section className="surface-card">
        <div className="surface-heading"><div><h2>Self-hosted adoption</h2><p>Opt-in installation heartbeats</p></div></div>
        {metricsError ? <div className="security-notice"><strong>Telemetry unavailable</strong><p>{metricsError}. Enable COHORT_TELEMETRY_COLLECTOR_ENABLED on the hosted API.</p></div> : <>
          <div className="setting-line"><span>Total installation IDs</span><code>{metrics ? metrics.self_hosted_installations_total : "Loading…"}</code></div>
          <div className="setting-line"><span>Seen in last 30 days</span><code>{metrics ? metrics.self_hosted_installations_active_30d : "Loading…"}</code></div>
          {metrics?.versions.map(item => <div className="setting-line" key={item.version}><span>Version {item.version}</span><code>{item.installations}</code></div>)}
        </>}
        <div className="security-notice"><strong>Measurement caveat</strong><p>{metrics?.note || "Self-reported opt-in installation IDs. Not unique people, verified installs, or paying customers."}</p></div>
      </section>
      <section className="surface-card">
        <div className="surface-heading"><div><h2>GitHub repository traffic</h2><p>Archived rolling 14-day totals</p></div></div>
        {trafficError ? <div className="security-notice"><strong>Archive not available</strong><p>{trafficError}</p></div> : traffic?.snapshots?.length ? <div className="data-table-wrap"><table className="data-table"><thead><tr><th>SNAPSHOT</th><th>CLONES · 14D</th><th>UNIQUE CLONERS · 14D</th></tr></thead><tbody>{traffic.snapshots.slice(-14).reverse().map(row => <tr key={row.date}><td>{row.date}</td><td>{row.clones}</td><td>{row.unique_cloners}</td></tr>)}</tbody></table></div> : <p className="empty-copy">Loading GitHub traffic archive…</p>}
        <div className="security-notice"><strong>Interpretation</strong><p>Each row is GitHub’s rolling 14-day total on that snapshot date, not a single-day count. Cloners are not verified people or installations.</p></div>
      </section>
    </div>
  </div>;
}
