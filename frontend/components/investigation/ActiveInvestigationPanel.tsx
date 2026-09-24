import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, CircleHelp, FileText, MapPin } from "lucide-react";
import type { EvidenceRecord, WatchlistSummary } from "@/types/overview";

interface Props { watchlist: WatchlistSummary | null; records: EvidenceRecord[] }

export function ActiveInvestigationPanel({ watchlist, records }: Props) {
  const [tab, setTab] = useState<"Summary" | "Evidence" | "Locations">("Summary");
  const linked = watchlist ? records.filter(record => record.watchlist_id === watchlist.id) : [];

  return <section className="panel investigation-panel">
    <div className="panel-header"><div><span className="panel-kicker">02 / ACTIVE MONITORING</span><h2>Watchlist focus</h2></div><span className="panel-meta mono">{watchlist?.id.slice(0, 8).toUpperCase() ?? "NO SELECTION"}</span></div>
    {!watchlist ? <div className="panel-empty prominent"><CircleHelp size={23} /><strong>No watchlists yet</strong><span>Create a watchlist to connect locations and collected evidence.</span><Link href="/watchlists/new">Create watchlist <ArrowUpRight size={13} /></Link></div> : <>
      <div className="focus-header"><div className="focus-status"><span className={`status-dot ${watchlist.status === "ACTIVE" ? "on" : ""}`} />{watchlist.status.replaceAll("_", " ")}</div><span className={`priority priority-${watchlist.priority.toLowerCase()}`}>{watchlist.priority} PRIORITY</span><h3>{watchlist.title}</h3><p>{watchlist.objective || "No objective entered for this watchlist."}</p></div>
      <div className="focus-stats"><div><span>LINKED RECORDS</span><strong className="mono">{watchlist.record_count}</strong></div><div><span>OBSERVED SOURCES</span><strong className="mono">{watchlist.source_count}</strong></div><div><span>LOCATIONS</span><strong className="mono">{watchlist.locations.length}</strong></div></div>
      <div className="focus-tabs" role="tablist" aria-label="Watchlist details">{(["Summary", "Evidence", "Locations"] as const).map(item => <button role="tab" aria-selected={tab === item} className={tab === item ? "active" : ""} onClick={() => setTab(item)} key={item}>{item}</button>)}</div>
      <div className="focus-content">
        {tab === "Summary" && <><div className="detail-line"><span>UPDATED</span><strong className="mono">{new Date(watchlist.updated_at).toISOString().replace("T", " ").slice(0, 16)} UTC</strong></div><div className="detail-line"><span>RECORD QUALITY</span><strong>Shown per evidence record</strong></div><div className="detail-line"><span>CORROBORATION</span><strong>Requires analyst review</strong></div><div className="explanation">Source count means distinct source labels in linked records. It does not imply independent corroboration or an intelligence confidence score.</div></>}
        {tab === "Evidence" && (linked.length ? linked.slice(0, 8).map(record => <div className="focus-list-row" key={record.id}><FileText size={14} /><span><strong>{record.title}</strong><small>{record.source} · {record.type}</small></span></div>) : <div className="inline-empty">No evidence linked to this watchlist.</div>)}
        {tab === "Locations" && (watchlist.locations.length ? watchlist.locations.map(location => <div className="focus-list-row" key={location.id}><MapPin size={14} /><span><strong>{location.name}</strong><small className="mono">{location.latitude === null ? "Coordinates not set" : `${location.latitude.toFixed(4)}°, ${location.longitude?.toFixed(4)}°`}</small></span></div>) : <div className="inline-empty">No locations added to this watchlist.</div>)}
      </div>
      <Link className="panel-action" href="/watchlists">Open watchlists <ArrowUpRight size={13} /></Link>
    </>}
  </section>;
}
