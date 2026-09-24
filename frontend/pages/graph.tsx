import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowUpRight } from "lucide-react";
import { getOverview, getSourceAudit, getSourceOutputs, tokenKey } from "@/lib/api";
import type { Overview, RawCollectionPage, SourceAudit } from "@/types/overview";

const emptyPage: RawCollectionPage = { items: [], total: 0, page: 1, size: 30 };
const sourceUrl = (value: string | null | undefined) => {
  try { const url = new URL(value || ""); return ["http:", "https:"].includes(url.protocol) ? url.href : null; }
  catch { return null; }
};

export default function Graph() {
  const [audit, setAudit] = useState<SourceAudit | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [outputs, setOutputs] = useState<RawCollectionPage>(emptyPage);
  const [type, setType] = useState<"RSS_ENTRY" | "SOURCE_ATTEMPT">("RSS_ENTRY");
  const [source, setSource] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const query = useMemo(() => new URLSearchParams({ type, source, q: search, page: String(page), size: "30" }).toString(), [type, source, search, page]);

  useEffect(() => {
    const token = sessionStorage.getItem(tokenKey);
    if (!token) { queueMicrotask(() => setReady(true)); return; }
    let active = true;
    let timer = 0;
    const update = async () => {
      try {
        const [nextAudit, nextOutputs, nextOverview] = await Promise.all([getSourceAudit(token), getSourceOutputs(token, query), getOverview(token)]);
        if (!active) return;
        setAudit(nextAudit); setOutputs(nextOutputs); setOverview(nextOverview); setReady(true); setError("");
        setSelectedId(current => nextOutputs.items.some(item => item.id === current) ? current : nextOutputs.items[0]?.id ?? null);
        timer = window.setTimeout(update, nextAudit.status === "RUNNING" ? 3_000 : 15_000);
      } catch (cause) {
        if (active) { setError(cause instanceof Error ? cause.message : "Graph unavailable"); setReady(true); timer = window.setTimeout(update, 15_000); }
      }
    };
    void update();
    return () => { active = false; window.clearTimeout(timer); };
  }, [query]);

  const selected = outputs.items.find(item => item.id === selectedId) ?? outputs.items[0] ?? null;
  const pages = Math.max(1, Math.ceil(outputs.total / outputs.size));
  const chronology = outputs.items.filter(item => item.type === "RSS_ENTRY" && item.published && !Number.isNaN(Date.parse(item.published))).sort((a, b) => Date.parse(b.published!) - Date.parse(a.published!));

  function chooseType(next: typeof type) { setType(next); setPage(1); setSelectedId(null); }
  function chooseSource(next: string) { setSource(next); setPage(1); setSelectedId(null); }

  return <main className="management-page graph-page"><div className="management-bar"><Link href="/"><ArrowLeft size={15} /> Back to Overview</Link><strong>TRINETRA / SOURCE GRAPH</strong></div>
    <div className="management-content"><span className="eyebrow">UNVALIDATED COLLECTION / PROVENANCE</span><h1>Source graph</h1><p>Explore what each site yielded. A feed entry is a collected claim, not a verified real-world event. Open an incident workspace for validated evidence and its lineage.</p>
      {error && <div className="form-error" role="alert">{error}</div>}
      {!ready ? <p>Loading graph…</p> : !sessionStorage.getItem(tokenKey) ? <p>Sign in on the <Link href="/">Overview</Link> to view the graph.</p> : <>
        <div className="audit-summary"><div><span>SCANNED SITES</span><strong>{audit?.summary.completed ?? "—"} / {audit?.summary.total ?? "—"}</strong></div><div><span>RSS ENTRIES</span><strong>{audit?.summary.rss_entries ?? "—"}</strong></div><div><span>FAILED / BLOCKED / FORBIDDEN</span><strong>{audit ? `${audit.summary.failed} / ${audit.summary.blocked} / ${audit.summary.forbidden}` : "—"}</strong></div><div><span>CANONICAL RECORDS</span><strong>{overview?.metrics.canonical_records ?? "—"}</strong></div></div>
        <section className="graph-incidents"><h2>Incident workspaces</h2><div className="graph-watchlists">{overview?.watchlists.map(item => <Link key={item.id} href={`/incidents/${encodeURIComponent(item.id)}`}><strong>{item.title}</strong><span>{item.priority} priority · {item.record_count} validated records · {item.locations.length} locations</span><small>Open incident graph →</small></Link>)}{!overview?.watchlists.length && <p>No watchlists are available.</p>}</div></section>
        <div className="audit-toolbar"><h2>Collection lineage</h2><span className="mono">{outputs.total} {type === "RSS_ENTRY" ? "RSS ENTRIES" : "SOURCE ATTEMPTS"}</span></div>
        <div className="collection-filters"><div className="graph-mode" role="group" aria-label="Graph data type"><button aria-pressed={type === "RSS_ENTRY"} onClick={() => chooseType("RSS_ENTRY")}>Extracted entries</button><button aria-pressed={type === "SOURCE_ATTEMPT"} onClick={() => chooseType("SOURCE_ATTEMPT")}>All site attempts</button></div><input aria-label="Filter graph by source" placeholder="Source name" value={source} onChange={event => chooseSource(event.target.value)} /><input aria-label="Search graph nodes" placeholder="Title or URL" value={search} onChange={event => { setSearch(event.target.value); setPage(1); setSelectedId(null); }} /></div>
        <div className="graph-layout"><div className="graph-rows">{outputs.items.map(item => <div className={`incident-graph-row ${item.id === selected?.id ? "selected" : ""}`} key={item.id}>
          <button className="graph-node graph-source" onClick={() => chooseSource(item.source)}><span>SOURCE SITE</span><strong>{item.source}</strong><small>{item.source_id}</small></button><span className="graph-edge" aria-hidden="true">→</span>
          {item.type === "RSS_ENTRY" && <><div className="graph-node"><span>RSS FEED</span><strong>{item.feed_url || "Feed URL unavailable"}</strong><small>{item.rss_type || "Feed type unknown"}</small></div><span className="graph-edge" aria-hidden="true">→</span></>}
          <button className="graph-node graph-record" aria-pressed={item.id === selected?.id} onClick={() => setSelectedId(item.id)}><span>{item.type === "RSS_ENTRY" ? "RAW EXTRACTED ENTRY" : "HOMEPAGE ATTEMPT"}</span><strong>{item.title}</strong><small>{item.status.replaceAll("_", " ")}{item.http_status ? ` · HTTP ${item.http_status}` : ""}</small></button>
        </div>)}{!outputs.items.length && <div className="inline-empty">No outputs match these filters.</div>}</div>
        <aside className="graph-inspector"><span className="eyebrow">SELECTED NODE / UNVALIDATED</span>{selected ? <><h2>{selected.title}</h2><p>{selected.source} · {selected.status.replaceAll("_", " ")}</p>{selected.summary && <div className="extracted-summary"><strong>Extracted summary</strong><p>{selected.summary}</p></div>}<dl>{Object.entries(selected).filter(([key, value]) => !["title", "source", "summary"].includes(key) && value !== null && value !== undefined && value !== "" && (!Array.isArray(value) || value.length > 0)).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{Array.isArray(value) ? value.join(", ") : String(value)}</dd></div>)}</dl>{sourceUrl(selected.url) ? <a href={sourceUrl(selected.url)!} target="_blank" rel="noopener noreferrer">View source <ArrowUpRight size={12} /></a> : <span>Source link unavailable</span>}</> : <p>Select a node to inspect the captured fields.</p>}</aside></div>
        <div className="pagination"><button disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button><span className="mono">PAGE {page} / {pages}</span><button disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button></div>
        <section id="timeline" className="graph-chronology"><h2>Published feed chronology</h2><p>Dates supplied by RSS feeds for the entries on this page. They do not establish when an incident occurred.</p>{chronology.length ? chronology.map(item => <button key={item.id} onClick={() => { setSelectedId(item.id); document.querySelector(".graph-inspector")?.scrollIntoView({ behavior: "smooth", block: "center" }); }}><time>{new Date(item.published!).toISOString().slice(0, 16).replace("T", " ")} UTC</time><strong>{item.title}</strong><span>{item.source}</span></button>) : <div className="inline-empty">No publication dates in these outputs. Choose Extracted entries to see feed chronology.</div>}</section>
        <Link href="/collection">Browse every raw field and output in Collections →</Link>
      </>}
    </div>
  </main>;
}
