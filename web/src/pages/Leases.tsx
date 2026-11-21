import { useEffect, useState } from "react";
import { Lock } from "lucide-react";
import { api } from "../lib/api";
import { Card, Disconnected, Empty, PageHead, TableSkeleton, Tag } from "../components/ui";
import { countdown } from "../lib/format";
import type { Lease } from "../lib/types";
import type { Ctx } from "./ctx";

export default function Leases({ ctx }: { ctx: Ctx }) {
  const { data } = ctx;
  const [agent, setAgent] = useState("operator"); const [key, setKey] = useState(""); const [seconds, setSeconds] = useState("60"); const [now, setNow] = useState(Date.now());
  useEffect(() => { const id = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(id); }, []);
  const acquire = () => void ctx.run(async () => { await api("/leases", { method: "POST", body: JSON.stringify({ agent_id: agent.trim(), key: key.trim(), duration_seconds: Number(seconds) || 60 }) }); setKey(""); }, "Lease acquired");
  const release = (l: Lease) => void ctx.run(() => api(`/leases/${encodeURIComponent(l.key)}?agent_id=${encodeURIComponent(l.agent_id)}`, { method: "DELETE" }), "Lease released");
  return <div className="page">
    <PageHead title="Leases" description="Temporary claims on shared keys, with expiry and fencing tokens that prevent stale writers." />
    {data.error && <Disconnected message={data.error} onRetry={ctx.refresh} />}
    <div className="grid">
      <Card className="c8" title="Active leases" description={data.settings ? (data.settings.require_leases ? "Writes require a lease on the key" : "Leases are advisory — writes do not require them") : undefined}>
        {!data.loaded ? <TableSkeleton rows={3} /> : <div className="tbl-wrap"><table><thead><tr><th>Resource</th><th>Agent</th><th className="num">Fencing token</th><th className="num">Expires in</th><th /></tr></thead><tbody>
          {data.leases.map((l) => { const left = l.expires_at - now / 1000; return <tr key={`${l.key}-${l.agent_id}`}>
            <td><strong className="data">{l.key}</strong></td><td>{l.agent_id}</td><td className="num">{l.fencing_token}</td>
            <td className="num">{left < 15 ? <Tag tone="warn">{countdown(l.expires_at, now)}</Tag> : countdown(l.expires_at, now)}</td>
            <td><div className="cell-actions"><button className="btn btn-link" disabled={ctx.busy} onClick={() => release(l)}>Release</button></div></td></tr>; })}
          {!data.leases.length && <tr><td colSpan={5}><Empty icon={<Lock size={20} />} title="No active leases">Agents acquire a lease before changing a key that others might touch.</Empty></td></tr>}
        </tbody></table></div>}
      </Card>
      <Card className="c4" title="Acquire a lease" description="Claim a key on behalf of an agent" flush={false}>
        <div className="stack">
          <label className="field">Agent ID<input value={agent} onChange={(e) => setAgent(e.target.value)} /></label>
          <label className="field">Resource key<input value={key} onChange={(e) => setKey(e.target.value)} placeholder="shared/resource" /></label>
          <label className="field">Duration (seconds)<input type="number" min={1} max={86400} value={seconds} onChange={(e) => setSeconds(e.target.value)} /></label>
          <button className="btn btn-primary" disabled={ctx.busy || !key.trim() || !agent.trim()} onClick={acquire}>Acquire lease</button>
        </div>
      </Card>
    </div>
  </div>;
}
