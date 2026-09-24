import { GitBranch } from "lucide-react";
import type { EvidenceRecord, Lineage } from "@/types/overview";

interface Props { lineage: Lineage | null; selectedRecord: EvidenceRecord | null; error: boolean }

export function SourceLineageGraph({ lineage, selectedRecord, error }: Props) {
  return <section className="panel lineage-panel">
    <div className="panel-header"><div><span className="panel-kicker">04 / PROVENANCE</span><h2>Source lineage</h2></div><span className="panel-meta mono">{selectedRecord?.id.slice(0, 12) ?? "NO RECORD"}</span></div>
    {!selectedRecord ? <div className="panel-empty"><GitBranch size={20} /><strong>No canonical record selected</strong><span>Choose an evidence record to inspect its origin.</span></div> : !lineage ? <div className="panel-empty"><GitBranch size={20} /><strong>{error ? "Lineage unavailable" : "Loading lineage"}</strong><span>{error ? "The lineage endpoint did not return a record." : "Checking source and raw evidence links."}</span></div> : <div className="lineage-scroll">
      <div className="lineage-flow">
        <div className="lineage-node"><span>SOURCE</span><strong>{lineage.source?.name || "Source unavailable"}</strong><small>{lineage.source?.category || "No source linked"}</small></div>
        <div className="lineage-connector" aria-hidden="true" />
        <div className="lineage-node"><span>RAW EVIDENCE</span><strong>{lineage.raw?.id || "No raw object linked"}</strong><small>{lineage.raw ? new Date(lineage.raw.retrieved_at).toISOString().slice(0, 16).replace("T", " ") + " UTC" : "Origin not stored"}</small></div>
        <div className="lineage-connector" aria-hidden="true" />
        <div className="lineage-node canonical"><span>CANONICAL RECORD</span><strong>{lineage.record.title}</strong><small className="mono">{lineage.record.id}</small></div>
      </div>
      <div className="lineage-destinations"><span className="mini-heading">LINKED CONTEXT</span><div>{lineage.watchlist ? <div className="lineage-chip"><span>WATCHLIST</span>{lineage.watchlist.name}</div> : <div className="lineage-chip muted">No watchlist link</div>}{lineage.related.map(item => <div className="lineage-chip" key={item.id}><span>CLUSTER MEMBER · {item.source}</span>{item.title}</div>)}</div></div>
      <div className="lineage-note">Cluster membership is a duplicate relationship, not independent corroboration.</div>
    </div>}
  </section>;
}
