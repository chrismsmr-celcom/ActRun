import { FileText, Menu, RefreshCw, Search } from "lucide-react";
import { DOCS_URL, REPO_URL } from "../lib/api";
import { GithubMark } from "./ui";

export default function Topbar({ crumb, connected, loaded, onSearch, onRefresh, onMenu }: { crumb: string; connected: boolean; loaded: boolean; onSearch: () => void; onRefresh: () => void; onMenu: () => void }) {
  const mac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);
  return <header className="topbar">
    <button className="icon-btn mobile-only" onClick={onMenu} aria-label="Open navigation"><Menu size={18} /></button>
    <div className="crumbs"><span>Workspace</span><span>/</span><strong>{crumb}</strong></div>
    <div className="top-actions">
      <button className="search-btn" onClick={onSearch} aria-label="Search"><Search size={16} /><span>Search</span><kbd>{mac ? "⌘" : "Ctrl"} K</kbd></button>
      <a className="top-link" href={DOCS_URL} target="_blank" rel="noreferrer"><FileText size={16} /><span>Doc</span></a>
      <a className="icon-btn" href={REPO_URL} target="_blank" rel="noreferrer" aria-label="Cohort on GitHub" title="GitHub repository"><GithubMark /></a>
      <span className={`live ${!loaded ? "" : connected ? "on" : "off"}`} role="status"><i /><span>{!loaded ? "Connecting" : connected ? "Live" : "Offline"}</span></span>
      <button className="icon-btn" onClick={onRefresh} aria-label="Refresh data" title="Refresh data"><RefreshCw size={16} /></button>
    </div>
  </header>;
}
