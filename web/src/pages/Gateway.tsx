import { useMemo, useState } from "react";
import { Cable, Copy, Plus } from "lucide-react";
import { API_BASE, api, isUnavailable } from "../lib/api";
import { Card, Disconnected, Empty, PageHead, Seg, TableSkeleton, Tag, useToast } from "../components/ui";
import { timeAgo } from "../lib/format";
import { useOptional } from "../lib/useCohort";
import type { GatewayAgent } from "../lib/types";
import type { Ctx } from "./ctx";

type Row = { id: string; source: "Observed" | "Registered"; kind: string; status: "active" | "idle" | "inactive" | GatewayAgent["status"]; last: string | null; events: number; branches: number; leases: number };
const statusTag = (s: Row["status"]) => s === "active" || s === "connected" ? <Tag tone="ok">{s === "active" ? "Active" : "Connected"}</Tag> : s === "idle" ? <Tag tone="warn">Idle</Tag> : s === "error" ? <Tag tone="err">Error</Tag> : <Tag>{s === "inactive" ? "Inactive" : "Disconnected"}</Tag>;

export default function Gateway({ ctx }: { ctx: Ctx }) {
  const { data } = ctx; const toast = useToast();
  const registry = useOptional<{ items: GatewayAgent[] }>("/gateway/agents", 15000);
  const [snippet, setSnippet] = useState<"mcp" | "http" | "python">("mcp");
  const [name, setName] = useState(""); const [kind, setKind] = useState("mcp"); const [endpoint, setEndpoint] = useState(""); const [saving, setSaving] = useState(false);
  const base = API_BASE || window.location.origin;

  const rows = useMemo<Row[]>(() => {
    const map = new Map<string, Row>();
    const get = (id: string): Row => { let r = map.get(id); if (!r) { r = { id, source: "Observed", kind: "—", status: "inactive", last: null, events: 0, branches: 0, leases: 0 }; map.set(id, r); } return r; };
    data.events.forEach((e) => { const r = get(e.agent_id); r.events++; if (!r.last || e.timestamp > r.last) r.last = e.timestamp; });
    data.branches.forEach((b) => { get(b.agent_id).branches++; });
    data.leases.forEach((l) => { get(l.agent_id).leases++; });
    map.forEach((r) => { if (r.last) { const age = Date.now() - new Date(r.last).getTime(); r.status = age < 5 * 60e3 ? "active" : age < 3600e3 ? "idle" : "inactive"; } });
    (registry.data?.items || []).forEach((a) => { const r = get(a.id || a.name); r.source = "Registered"; r.kind = a.kind; r.status = a.status; r.last = a.last_seen || r.last; });
    return [...map.values()].sort((a, b) => (b.last || "").localeCompare(a.last || ""));
  }, [data.events, data.branches, data.leases, registry.data]);

  const snippets = {
    mcp: `# 1. Install the Python package, then the MCP server\npython -m pip install -e "./python"\ncd integrations/mcp-server && python -m pip install -e .\n\n# 2. Register it in your MCP client\n{\n  "mcpServers": {\n    "cohort": { "command": "cerbere-cohort-mcp" }\n  }\n}`,
    http: `# Create a branch for an agent\ncurl -X POST ${base}/api/branches \\\n  -H "Content-Type: application/json" \\\n  -H "X-Organization-ID: <organization-id>" \\\n  -H "Authorization: Bearer <access-token>" \\\n  -d '{"agent_id": "agent-backend", "name": "implement-api"}'`,
    python: `from cerbere_cohort.persistence import PersistentWorkspace\n\nwith PersistentWorkspace("workspace.db") as workspace:\n    branch = workspace.create_branch("agent-a", "task-1")\n    branch.set("task/status", "complete")\n    workspace.commit("agent-a", branch)`,
  };
  const register = async () => {
    setSaving(true);
    try { await api("/gateway/agents", { method: "POST", body: JSON.stringify({ name: name.trim(), kind, endpoint: endpoint.trim() || null }) }); toast("Agent registered"); setName(""); setEndpoint(""); registry.reload(); }
    catch (e) { toast(isUnavailable(e) ? "The gateway registry endpoint is not available on this API yet." : e instanceof Error ? e.message : "Could not register agent", "err"); }
    finally { setSaving(false); }
  };
  return <div className="page">
    <PageHead title="Gateway" description="Connect agents to this workspace and see which ones are talking to it." />
    {data.error && <Disconnected message={data.error} onRetry={ctx.refresh} />}
    <div className="grid">
      <Card className="c8" title="Agents" description="Seen in events, branches and leases, plus any registered through the gateway"
        actions={registry.status === "unavailable" ? <Tag>Registry not connected</Tag> : registry.status === "ready" ? <Tag tone="ok">Registry connected</Tag> : undefined}>
        {!data.loaded ? <TableSkeleton /> : <div className="tbl-wrap"><table><thead><tr><th>Agent</th><th>Source</th><th>Status</th><th className="num">Events</th><th className="num">Branches</th><th className="num">Leases</th><th className="num">Last activity</th></tr></thead><tbody>
          {rows.map((r) => <tr key={r.id}><td><strong>{r.id}</strong></td><td>{r.source === "Registered" ? `Registered · ${r.kind}` : "Observed"}</td><td>{statusTag(r.status)}</td><td className="num">{r.events}</td><td className="num">{r.branches}</td><td className="num">{r.leases}</td><td className="num">{r.last ? timeAgo(r.last) : "—"}</td></tr>)}
          {!rows.length && <tr><td colSpan={7}><Empty icon={<Cable size={20} />} title="No agents connected yet">Connect an agent with the instructions on the right. It will appear here as soon as it creates a branch or writes an event.</Empty></td></tr>}
        </tbody></table></div>}
      </Card>
      <Card className="c4" title="Connect an agent" description="Pick how your agent talks to Cohort" flush={false}>
        <div className="stack">
          <Seg label="Connection type" value={snippet} onChange={setSnippet} options={[{ id: "mcp", label: "MCP" }, { id: "http", label: "HTTP API" }, { id: "python", label: "Python" }]} />
          <pre className="code">{snippets[snippet]}</pre>
          <button className="btn btn-secondary" onClick={() => void navigator.clipboard?.writeText(snippets[snippet]).then(() => toast("Snippet copied"))}><Copy size={14} />Copy snippet</button>
          {snippet === "mcp" && <p className="muted">MCP is a local stdio integration today, not a hosted multi-user service.</p>}
        </div>
      </Card>
      <Card className="c12" title="Register an agent" description="Add an agent to the gateway registry so its status is tracked here" flush={false}>
        <div className="row" style={{ alignItems: "flex-end", flexWrap: "wrap" }}>
          <label className="field" style={{ flex: "1 1 200px" }}>Agent name<input value={name} onChange={(e) => setName(e.target.value)} placeholder="agent-backend" /></label>
          <label className="field" style={{ flex: "0 1 160px" }}>Type<select value={kind} onChange={(e) => setKind(e.target.value)}><option value="mcp">MCP</option><option value="http">HTTP</option><option value="sdk">Python SDK</option></select></label>
          <label className="field" style={{ flex: "2 1 280px" }}>Endpoint (optional)<input value={endpoint} onChange={(e) => setEndpoint(e.target.value)} placeholder="https://agent.example.com/hook" /></label>
          <button className="btn btn-primary" disabled={saving || !name.trim()} onClick={() => void register()}><Plus size={16} />Register</button>
        </div>
      </Card>
    </div>
  </div>;
}
