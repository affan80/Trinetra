import { useRef, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, CircleHelp, FileText, MapPin } from "lucide-react";
import type { EvidenceRecord, WatchlistSummary } from "@/types/overview";

interface Props { watchlist: WatchlistSummary | null; records: EvidenceRecord[] }

export function ActiveInvestigationPanel({ watchlist, records }: Props) {
  const [tab, setTab] = useState<"Summary" | "Evidence" | "Locations">("Summary");
  const bodyRef = useRef<HTMLDivElement>(null);
  const linked = watchlist ? records.filter(record => record.watchlist_id === watchlist.id) : [];

  return <section className="panel investigation-panel">
    <div className="panel-header"><div><span className="panel-kicker">02 / ACTIVE MONITORING</span><h2>Watchlist focus</h2></div><span className="panel-meta mono">{watchlist?.id.slice(0, 8).toUpperCase() ?? "NO SELECTION"}</span></div>
    {!watchlist ? <div className="panel-empty prominent"><CircleHelp size={23} /><strong>No watchlists yet</strong><span>Create a watchlist to connect locations and collected evidence.</span><Link href="/watchlists/new">Create watchlist <ArrowUpRight size={13} /></Link></div> : <>
      <div className="investigation-body" ref={bodyRef} tabIndex={0} aria-label="Scrollable watchlist details">
      <div className="focus-header"><div className="focus-top"><div className="focus-status"><span className={`status-dot ${watchlist.status === "ACTIVE" ? "on" : ""}`} />{watchlist.status.replaceAll("_", " ")}</div><span className={`priority priority-${watchlist.priority.toLowerCase()}`}>{watchlist.priority} PRIORITY</span></div><h3>{watchlist.title}</h3><p>{watchlist.objective || "No objective entered for this watchlist."}</p></div>
      <div className="focus-stats"><div><span>LINKED RECORDS</span><strong className="mono">{watchlist.record_count}</strong></div><div><span>OBSERVED SOURCES</span><strong className="mono">{watchlist.source_count}</strong></div><div><span>LOCATIONS</span><strong className="mono">{watchlist.locations.length}</strong></div></div>
      <div className="focus-tabs" role="tablist" aria-label="Watchlist details">{(["Summary", "Evidence", "Locations"] as const).map(item => <button role="tab" aria-selected={tab === item} className={tab === item ? "active" : ""} onClick={() => setTab(item)} key={item}>{item}</button>)}</div>
      <div className="focus-content">
        {tab === "Summary" && <><div className="detail-line"><span>UPDATED</span><strong className="mono">{new Date(watchlist.updated_at).toISOString().replace("T", " ").slice(0, 16)} UTC</strong></div><div className="detail-line"><span>LATEST EVIDENCE</span><strong>{linked[0]?.title || "None linked"}</strong></div><div className="detail-line"><span>RECORD QUALITY</span><strong>{linked[0]?.quality_status || "Unassessed"}</strong></div><div className="detail-line"><span>CORROBORATION</span><strong>Requires analyst review</strong></div>{linked.some(record => record.demo) && <div className="demo-notice">Demo record: no article text was collected.</div>}<div className="explanation">Open the full workspace for source lineage, extracted text, and the complete timeline.</div></>}
        {tab === "Evidence" && (linked.length ? linked.map(record => <div className="focus-list-row" key={record.id}><FileText size={14} /><span><strong>{record.title}</strong><small>{record.source} · {record.type}{record.demo ? " · DEMO RECORD" : ""}</small>{record.url && /^https?:\/\//i.test(record.url) ? <a href={record.url} target="_blank" rel="noopener noreferrer">View source <ArrowUpRight size={11} /></a> : <small>Source link unavailable</small>}</span></div>) : <div className="inline-empty">No evidence linked to this watchlist.</div>)}
        {tab === "Locations" && (watchlist.locations.length ? watchlist.locations.map(location => <div className="focus-list-row" key={location.id}><MapPin size={14} /><span><strong>{location.name}</strong><small className="mono">{location.latitude === null ? "Coordinates not set" : `${location.latitude.toFixed(4)}°, ${location.longitude?.toFixed(4)}°`}</small></span></div>) : <div className="inline-empty">No locations added to this watchlist.</div>)}
      </div>
      </div>
      <div className="panel-actions"><button className="panel-action" onClick={() => bodyRef.current?.scrollBy({ top: bodyRef.current.clientHeight, behavior: "smooth" })}>More details ↓</button><Link className="panel-action" href={`/incidents/${encodeURIComponent(watchlist.id)}${watchlist.locations[0] ? `?location=${encodeURIComponent(watchlist.locations[0].id)}` : ""}`}>Open full workspace <ArrowUpRight size={13} /></Link></div>
    </>}
  </section>;
}
