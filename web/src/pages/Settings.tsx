import { API_BASE } from "../lib/api";
import { getActiveWorkspaceId } from "../auth";
import { Card, Disconnected, PageHead, Seg, Tag } from "../components/ui";
import type { SidebarMode } from "../components/Sidebar";
import type { Ctx } from "./ctx";

const Line = ({ label, value }: { label: string; value: string }) => <div className="kv"><span>{label}</span><span className="data">{value}</span></div>;
export default function Settings({ ctx, dark, setDark, mode, setMode }: { ctx: Ctx; dark: boolean; setDark: (v: boolean) => void; mode: SidebarMode; setMode: (m: SidebarMode) => void }) {
  const s = ctx.data.settings;
  return <div className="page">
    <PageHead title="Setting" description="Inspect the configuration and operational limits of this Cohort instance." />
    {ctx.data.error && <Disconnected message={ctx.data.error} onRetry={ctx.refresh} />}
    <div className="grid">
      <Card className="c6" title="Storage and coordination" description="Reported by /api/settings">
        <Line label="Storage backend" value={s?.persistence || "—"} /><Line label="Database path" value={s?.database_path || "—"} />
        <Line label="Lease enforcement" value={s ? (s.require_leases ? "Required for writes" : "Advisory") : "—"} />
        <Line label="Database transactions" value={s ? (s.database_transactions ? "Yes" : "No") : "—"} />
      </Card>
      <Card className="c6" title="Runtime capabilities" description="Features reported by the API adapter">
        <Line label="Multi-process coordination" value={s ? (s.multi_process ? "Enabled" : "Single process") : "—"} />
        <Line label="Authentication" value={s ? (s.authentication === "supabase" ? "Supabase JWT + membership checks" : "Not configured (development)") : "—"} />
        <div style={{ padding: "16px 24px 24px" }}><div className="notice warn"><div className="grow"><strong>Deployment note</strong>Workspace access is selected per signed-in user. Membership is checked by the API on each request.</div></div></div>
      </Card>
      <Card className="c6" title="Appearance" description="Saved in this browser">
        <div className="kv"><span>Theme</span><Seg label="Theme" value={dark ? "dark" : "light"} onChange={(v) => setDark(v === "dark")} options={[{ id: "light", label: "Light" }, { id: "dark", label: "Dark" }]} /></div>
        <div className="kv"><span>Sidebar</span><Seg label="Sidebar mode" value={mode} onChange={setMode} options={[{ id: "expanded", label: "Expanded" }, { id: "hover", label: "On hover" }, { id: "collapsed", label: "Collapsed" }]} /></div>
      </Card>
      <Card className="c6" title="API connection" description="Set at build time with VITE_* variables">
        <Line label="API base URL" value={API_BASE || "Same origin (proxied to /api)"} />
        <Line label="Active workspace ID" value={getActiveWorkspaceId() ? `${getActiveWorkspaceId().slice(0, 8)}…` : "Not selected"} />
        <div className="kv"><span>Status</span>{ctx.data.connected ? <Tag tone="ok">Connected</Tag> : <Tag tone="err">Offline</Tag>}</div>
      </Card>
    </div>
  </div>;
}
