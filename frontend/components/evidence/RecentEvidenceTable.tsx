import { useState } from "react";
import { FileSearch } from "lucide-react";
import type { EvidenceRecord } from "@/types/overview";

interface Props { records: EvidenceRecord[]; selectedId: string | null; onSelect: (id: string) => void }

export function RecentEvidenceTable({ records, selectedId, onSelect }: Props) {
  const [filter, setFilter] = useState("All types");
  const types = [...new Set(records.map(record => record.type))].sort();
  const visible = filter === "All types" ? records : records.filter(record => record.type === filter);

  return <section className="panel evidence-panel">
    <div className="panel-header"><div><span className="panel-kicker">03 / COLLECTION</span><h2>Recent evidence</h2></div><select aria-label="Filter evidence type" value={filter} onChange={event => setFilter(event.target.value)}><option>All types</option>{types.map(type => <option key={type}>{type}</option>)}</select></div>
    <div className="evidence-columns mono"><span>TIME (UTC)</span><span>RECORD / DESCRIPTION</span><span>SOURCE</span><span>QUALITY</span></div>
    <div className="panel-scroll">{visible.length ? visible.map(record => <button className={`evidence-row ${record.id === selectedId ? "selected" : ""}`} onClick={() => onSelect(record.id)} key={record.id}>
      <span className="mono timestamp">{new Date(record.timestamp).toISOString().slice(5, 16).replace("T", " ")}</span>
      <span className="evidence-title"><strong>{record.title}</strong><small className="mono">{record.id} · {record.type}</small></span>
      <span className="source-name">{record.source}</span>
      <span className={`quality ${record.quality_status === "VALID" ? "valid" : ""}`} title={record.quality_status || "No quality assessment"}>{record.quality_score === null ? "—" : `${Math.round(record.quality_score * 100)}%`}</span>
    </button>) : <div className="panel-empty"><FileSearch size={20} /><strong>No evidence records</strong><span>{filter === "All types" ? "Collected records will appear after normalization." : "No records match this type."}</span></div>}</div>
  </section>;
}
