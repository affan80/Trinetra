import type { ReactNode } from "react";
import Link from "next/link";
import { LogOut, RefreshCw, Search, ShieldCheck } from "lucide-react";
import { navigation } from "@/data/overview";

interface Props {
  children: ReactNode;
  generatedAt: string | null;
  query: string;
  onQueryChange: (value: string) => void;
  onRefresh: () => void;
  onSignOut: () => void;
  loading: boolean;
}

export function AppShell({ children, generatedAt, query, onQueryChange, onRefresh, onSignOut, loading }: Props) {
  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-symbol">◈</span><div><strong>TRINETRA</strong><small>EVIDENCE-CENTRIC OSINT</small></div></div>
      <label className="global-search"><Search size={15} /><input aria-label="Search visible evidence" placeholder="Search evidence, source or record ID" value={query} onChange={event => onQueryChange(event.target.value)} /></label>
      <nav className="top-actions" aria-label="Workspace modes"><span className="mode-active">EXPLORE</span><span>ANALYSE</span><span>CORRELATE</span><span>REPORT</span></nav>
      <div className="topbar-end">
        <div className="time-block"><span>DATA AS OF</span><strong className="mono">{generatedAt ? new Date(generatedAt).toISOString().replace("T", " ").slice(0, 19) : "—"} UTC</strong></div>
        <button className="header-icon" title="Refresh overview" aria-label="Refresh overview" onClick={onRefresh} disabled={loading}><RefreshCw size={15} className={loading ? "spinning" : ""} /></button>
        <div className="system-pill"><span className={generatedAt ? "status-dot on" : "status-dot"} />{generatedAt ? "API CONNECTED" : "CONNECTING"}</div>
        <button className="header-icon" title="Sign out" aria-label="Sign out" onClick={onSignOut}><LogOut size={15} /></button>
        <div className="avatar">AS</div>
      </div>
    </header>
    <aside className="sidebar">
      <div className="operation"><span className="eyebrow">WORKSPACE</span><strong><ShieldCheck size={14} /> Operational analysis</strong><small>Live evidence environment</small></div>
      <nav className="sidebar-nav" aria-label="Primary navigation">
        {navigation.map(group => <div className="nav-group" key={group.group}>
          <div className="nav-heading">{group.group}</div>
          {group.items.map(({ label, icon: Icon, href }) => href
            ? <Link key={label} href={href} className={`side-item ${label === "Overview" ? "active" : ""}`}><Icon size={15} />{label}</Link>
            : <span key={label} className="side-item unavailable" title="Workspace view not connected yet"><Icon size={15} />{label}</span>)}
        </div>)}
      </nav>
      <div className="sidebar-footer"><span className="status-dot on" /> API SESSION ACTIVE <small>TRINETRA v1.0.0</small></div>
    </aside>
    <main className="workspace-content">{children}</main>
  </div>;
}
