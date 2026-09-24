import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, FileSearch } from "lucide-react";
import type { EvidenceRecord, RawCollectionOutput } from "@/types/overview";

interface Props { records: EvidenceRecord[]; rawOutputs: RawCollectionOutput[]; selectedId: string | null; onSelect: (id: string) => void }

export function RecentEvidenceTable({ records, rawOutputs, selectedId, onSelect }: Props) {
  const [filter, setFilter] = useState("All types");
  const [mode, setMode] = useState<"validated" | "raw">("validated");
  const types = [...new Set(records.map(record => record.type))].sort();
  const visible = filter === "All types" ? records : records.filter(record => record.type === filter);

  return <section className="panel evidence-panel">
    <div className="panel-header"><div><span className="panel-kicker">03 / COLLECTION</span><h2>Recent evidence</h2></div>{mode === "validated" && <select aria-label="Filter evidence type" value={filter} onChange={event => setFilter(event.target.value)}><option>All types</option>{types.map(type => <option key={type}>{type}</option>)}</select>}</div>
    <div className="evidence-tabs" role="tablist"><button role="tab" aria-selected={mode === "validated"} onClick={() => setMode("validated")}>Validated Evidence</button><button role="tab" aria-selected={mode === "raw"} onClick={() => setMode("raw")}>Raw Collection</button></div>
    {mode === "raw" ? <div className="panel-scroll raw-overview"><strong>UNVALIDATED COLLECTION · CROSS-SOURCE PREVIEW</strong>{rawOutputs.map(item => <div key={item.id}><span>{item.title}</span><small>{item.source} · {item.type.replaceAll("_", " ")} · {item.status.replaceAll("_", " ")}</small></div>)}{!rawOutputs.length && <div className="inline-empty">No raw collection output.</div>}<Link href="/graph">Explore source graph →</Link><Link href="/collection">View all raw outputs →</Link></div> : <>
    <div className="evidence-columns mono"><span>TIME (UTC)</span><span>RECORD / DESCRIPTION</span><span>SOURCE</span><span>QUALITY</span><span>ACTIONS</span></div>
    <div className="panel-scroll">{visible.length ? visible.map(record => <div role="button" tabIndex={0} className={`evidence-row ${record.id === selectedId ? "selected" : ""}`} onClick={() => onSelect(record.id)} onKeyDown={event => { if (event.key === "Enter" || event.key === " ") onSelect(record.id); }} key={record.id}>
      <span className="mono timestamp">{new Date(record.timestamp).toISOString().slice(5, 16).replace("T", " ")}</span>
      <span className="evidence-title"><strong>{record.title}</strong><small className="mono">{record.id} · {record.type}{record.demo ? " · DEMO" : ""}</small></span>
      <span className="source-name">{record.source}</span>
      <span className={`quality ${record.quality_status === "VALID" ? "valid" : ""}`} title={record.quality_status || "No quality assessment"}>{record.quality_score === null ? "—" : `${Math.round(record.quality_score * 100)}%`}</span>
      <span className="evidence-actions">{record.watchlist_id && <Link href={`/incidents/${encodeURIComponent(record.watchlist_id)}`}>Open</Link>}{record.url && /^https?:\/\//i.test(record.url) ? <a href={record.url} target="_blank" rel="noopener noreferrer" onClick={event => event.stopPropagation()} aria-label={`View source for ${record.title}`}><ArrowUpRight size={11} /></a> : <span title="Source link unavailable">—</span>}</span>
    </div>) : <div className="panel-empty"><FileSearch size={20} /><strong>No evidence records</strong><span>{filter === "All types" ? "Collected records will appear after normalization." : "No records match this type."}</span></div>}</div></>}
  </section>;
}
