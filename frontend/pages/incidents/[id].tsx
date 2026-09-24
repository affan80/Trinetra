import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { ArrowLeft, ArrowUpRight, GitBranch } from "lucide-react";
import { OperationalMap } from "@/components/map/OperationalMap";
import { getIncident, tokenKey } from "@/lib/api";
import type { IncidentContext } from "@/types/overview";

const when = (value: string | null) => value ? new Date(value).toISOString().replace("T", " ").slice(0, 16) + " UTC" : "Not recorded";

export default function IncidentWorkspace() {
  const router = useRouter();
  const id = typeof router.query.id === "string" ? router.query.id : "";
  const locationId = typeof router.query.location === "string" ? router.query.location : null;
  const [incident, setIncident] = useState<IncidentContext | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!router.isReady || !id) return;
    const token = sessionStorage.getItem(tokenKey);
    if (!token) { queueMicrotask(() => setError("Sign in on the Overview to open this workspace.")); return; }
    let active = true;
    getIncident(id, token, locationId).then(data => {
      if (active) { setIncident(data); setSelectedId(current => data.records.some(record => record.id === current) ? current : data.records[0]?.id ?? null); setError(""); }
    }).catch(cause => { if (active) setError(cause instanceof Error ? cause.message : "Incident workspace unavailable"); });
    return () => { active = false; };
  }, [id, locationId, router.isReady]);

  if (error) return <main className="management-page"><div className="management-bar"><Link href="/"><ArrowLeft size={15} /> Back to Overview</Link></div><div className="management-content"><div className="form-error" role="alert">{error}</div></div></main>;
  if (!incident) return <main className="management-page"><div className="management-content">Loading incident workspace…</div></main>;

  const selected = incident.records.find(record => record.id === selectedId) ?? incident.records[0] ?? null;
  const selectedLocation = incident.locations.find(location => location.id === incident.selected_location_id) ?? incident.locations[0] ?? null;
  const mapWatchlist = { ...incident.watchlist, locations: incident.locations, record_count: incident.records.length, source_count: new Set(incident.records.map(record => record.source)).size };

  return <main className="incident-page">
    <div className="management-bar"><Link href="/"><ArrowLeft size={15} /> Back to Overview</Link><strong>INCIDENT WORKSPACE / {incident.watchlist.id.slice(0, 8).toUpperCase()}</strong></div>
    <div className="incident-content">
      <header className="incident-heading"><div><span className="eyebrow">WATCHLIST CONTEXT · {incident.watchlist.status} · {incident.watchlist.priority} PRIORITY</span><h1>{incident.watchlist.title}</h1><p>{incident.watchlist.objective || "No operational objective recorded."}</p>{incident.records.some(record => record.demo) && <p className="demo-notice">This workspace includes demo records. Their article text and original source links were not collected.</p>}</div><div className="mono">UPDATED {when(incident.watchlist.updated_at)}</div></header>

      <section className="panel incident-summary"><div className="panel-header"><div><span className="panel-kicker">01 / CONTEXT</span><h2>Operational summary</h2></div></div><div className="incident-summary-body"><p>{incident.watchlist.objective || "No summary has been recorded for this watchlist."}</p><div className="incident-stats"><div><strong>{incident.records.length}</strong><span>Validated records</span></div><div><strong>{mapWatchlist.source_count}</strong><span>Sources</span></div><div><strong>{incident.locations.length}</strong><span>Locations</span></div></div><dl><dt>Selected location</dt><dd>{selectedLocation?.name || "None"}</dd><dt>Created</dt><dd>{when(incident.watchlist.created_at)}</dd><dt>Updated</dt><dd>{when(incident.watchlist.updated_at)}</dd></dl><Link href="/collection">View unvalidated collection <ArrowUpRight size={12} /></Link></div></section>
      <div className="incident-map"><OperationalMap watchlists={[mapWatchlist]} selectedId={incident.watchlist.id} selectedLocationId={incident.selected_location_id} /></div>

      <section className="panel incident-lineage"><div className="panel-header"><div><span className="panel-kicker">02 / PROVENANCE</span><h2>Source lineage graph</h2></div><GitBranch size={16} /></div><div className="incident-graph-list">
        {incident.records.length ? incident.records.map(record => <div className={`incident-graph-row ${record.id === selected?.id ? "selected" : ""}`} key={record.id}>
          <div className="graph-node"><span>SOURCE</span><strong>{record.source}</strong><small>{record.source_id?.slice(0, 12) || "ID unavailable"}</small></div><span className="graph-edge" aria-hidden="true">→</span>
          <div className="graph-node"><span>RAW CAPTURE</span><strong>{record.raw?.id || "Not linked"}</strong><small>{record.raw ? when(record.raw.retrieved_at) : "No capture stored"}</small></div><span className="graph-edge" aria-hidden="true">→</span>
          <button className="graph-node graph-record" onClick={() => setSelectedId(record.id)} aria-pressed={record.id === selected?.id}><span>VALIDATED RECORD</span><strong>{record.title}</strong><small>{record.id}</small></button>
          {record.clusters.length > 0 && <><span className="graph-edge" aria-hidden="true">→</span><div className="graph-node"><span>DUPLICATE CLUSTER</span><strong>{record.clusters.map(cluster => cluster.relationship).join(", ")}</strong><small>{record.clusters.map(cluster => cluster.id.slice(0, 8)).join(", ")}</small></div></>}
        </div>) : <div className="inline-empty">No validated records are linked to this watchlist.</div>}
      </div><p className="graph-note">Select a record node to inspect its extracted text and capture details. Cluster links show duplicate relationships, not corroboration.</p></section>

      <section className="panel incident-evidence"><div className="panel-header"><div><span className="panel-kicker">03 / EVIDENCE</span><h2>Linked records</h2></div><span className="panel-meta mono">{incident.records.length} RECORDS</span></div><div className="panel-scroll">{incident.records.map(record => <button className={`incident-record ${record.id === selected?.id ? "selected" : ""}`} onClick={() => setSelectedId(record.id)} key={record.id}><strong>{record.title}</strong><span>{record.source}</span><span>{record.quality_status || "UNASSESSED"}</span></button>)}{!incident.records.length && <div className="panel-empty">No validated evidence is linked.</div>}</div></section>
      <section className="panel incident-detail"><div className="panel-header"><div><span className="panel-kicker">04 / EXTRACTED DATA</span><h2>Evidence details</h2></div></div>{selected ? <div className="incident-detail-body"><h3>{selected.title}</h3><dl>
        <dt>Record ID</dt><dd className="mono">{selected.id}</dd><dt>Evidence ID</dt><dd className="mono">{selected.evidence_id}</dd><dt>Source</dt><dd>{selected.source}</dd><dt>Type</dt><dd>{selected.type}</dd><dt>Language</dt><dd>{selected.language || "Not recorded"}</dd><dt>Quality</dt><dd>{selected.quality_status || "Unassessed"}{selected.quality_score === null ? "" : ` · ${Math.round(selected.quality_score * 100)}%`}</dd><dt>Published</dt><dd>{when(selected.published_at)}</dd><dt>Retrieved</dt><dd>{when(selected.retrieved_at)}</dd><dt>Normalized</dt><dd>{when(selected.created_at)}</dd>
        {selected.raw && <><dt>Raw capture</dt><dd className="mono">{selected.raw.id}</dd><dt>HTTP response</dt><dd>{selected.raw.http_status} · {selected.raw.content_type}</dd><dt>Captured size</dt><dd>{selected.raw.content_length.toLocaleString()} bytes</dd><dt>SHA-256</dt><dd className="mono">{selected.raw.sha256}</dd><dt>Adapter</dt><dd>{selected.raw.adapter_type}</dd>{selected.raw.provenance && <><dt>Collector</dt><dd>{selected.raw.provenance.collector_id} · {selected.raw.provenance.collector_version}</dd><dt>Method</dt><dd>{selected.raw.provenance.collection_method}</dd><dt>Observed</dt><dd>{when(selected.raw.provenance.observed_at)}</dd><dt>Redirects</dt><dd>{selected.raw.provenance.redirect_chain.length}</dd></>}</>}
      </dl><div className="incident-extracted"><h4>Extracted text</h4><p>{selected.plain_text || "No article text was stored for this record."}</p></div>{selected.content_blocks.length > 0 && <details><summary>Content blocks ({selected.content_blocks.length})</summary><pre>{JSON.stringify(selected.content_blocks, null, 2)}</pre></details>}{Object.keys(selected.processing_quality).length > 0 && <details><summary>Processing quality</summary><pre>{JSON.stringify(selected.processing_quality, null, 2)}</pre></details>}
      {selected.url ? <a href={selected.url} target="_blank" rel="noopener noreferrer">View original source <ArrowUpRight size={12} /></a> : <span className="source-unavailable">Source link unavailable</span>}</div> : <div className="panel-empty">No evidence selected.</div>}</section>

      <section className="panel incident-timeline"><div className="panel-header"><div><span className="panel-kicker">05 / CHRONOLOGY</span><h2>Evidence activity</h2></div><span className="panel-meta mono">{incident.timeline.length} OBSERVATIONS</span></div><div className="incident-timeline-list">{incident.timeline.map(entry => <div className={`incident-time-row ${entry.kind}`} key={entry.id}><time dateTime={entry.timestamp}>{when(entry.timestamp)}</time><span className="incident-time-dot" /><div><strong>{entry.title}</strong><p>{entry.detail}</p></div></div>)}{!incident.timeline.length && <div className="inline-empty">No chronology has been recorded.</div>}</div></section>
      <section className="panel incident-locations"><div className="panel-header"><div><span className="panel-kicker">06 / LOCATIONS</span><h2>Related locations</h2></div></div><div className="panel-scroll">{incident.locations.map(location => <Link className={location.id === incident.selected_location_id ? "selected" : ""} href={`/incidents/${encodeURIComponent(id)}?location=${encodeURIComponent(location.id)}`} key={location.id}><strong>{location.name}</strong><span>{[location.city, location.region, location.country].filter(Boolean).join(", ") || "Region unavailable"}</span><small className="mono">{location.latitude === null ? "Coordinates unavailable" : `${location.latitude.toFixed(4)}°, ${location.longitude?.toFixed(4)}°`}</small></Link>)}{!incident.locations.length && <div className="inline-empty">No locations are linked.</div>}</div></section>
    </div>
  </main>;
}
