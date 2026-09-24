import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowUpRight } from "lucide-react";
import { getSourceAudit, getSourceOutputs, request, tokenKey } from "@/lib/api";
import type { RawCollectionPage, SourceAudit } from "@/types/overview";

interface Job { id: string; query: string; status: string; attempts: number; source_id: string }

export default function Collection() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [audit, setAudit] = useState<SourceAudit | null>(null);
  const [outputs, setOutputs] = useState<RawCollectionPage>({ items: [], total: 0, page: 1, size: 50 });
  const [filters, setFilters] = useState({ q: "", type: "", source: "", status: "" });
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const query = useMemo(() => new URLSearchParams({ page: String(page), size: "50", ...filters }).toString(), [filters, page]);

  useEffect(() => {
    const token = sessionStorage.getItem(tokenKey);
    if (!token) { queueMicrotask(() => setReady(true)); return; }
    let active = true;
    let timer = 0;
    const update = async () => {
      try {
        const [nextJobs, nextAudit, nextOutputs] = await Promise.all([request<Job[]>("collection-jobs", token), getSourceAudit(token), getSourceOutputs(token, query)]);
        if (!active) return;
        setJobs(nextJobs); setAudit(nextAudit); setOutputs(nextOutputs); setError(""); setReady(true);
        timer = window.setTimeout(update, nextAudit.status === "RUNNING" ? 3_000 : 15_000);
      } catch (cause) {
        if (active) { setError(cause instanceof Error ? cause.message : "Collection status unavailable"); setReady(true); timer = window.setTimeout(update, 15_000); }
      }
    };
    void update();
    return () => { active = false; window.clearTimeout(timer); };
  }, [query]);

  const pages = Math.max(1, Math.ceil(outputs.total / outputs.size));
  return <main className="management-page"><div className="management-bar"><Link href="/"><ArrowLeft size={15} /> Overview</Link><strong>TRINETRA / COLLECTIONS</strong></div>
    <div className="management-content"><span className="eyebrow">UNVALIDATED COLLECTION</span><h1>Source collection</h1><p>Raw homepage attempts and RSS entries remain separate from validated evidence.</p>
      {error && <div className="form-error" role="alert">{error}</div>}
      {!ready ? <p>Loading…</p> : !sessionStorage.getItem(tokenKey) ? <p>Sign in on the <Link href="/">overview</Link> to view collection status.</p> : <>
        <div className="audit-summary">
          <div><span>SCAN STATUS</span><strong>{audit?.status.replaceAll("_", " ") ?? "UNAVAILABLE"}</strong></div>
          <div><span>PROGRESS</span><strong className="mono">{audit ? `${audit.summary.completed} / ${audit.summary.total}` : "—"}</strong></div>
          <div><span>CAPTURED</span><strong className="mono">{audit?.summary.collected ?? "—"}</strong></div>
          <div><span>FAILED / BLOCKED</span><strong className="mono">{audit ? `${audit.summary.failed} / ${audit.summary.blocked}` : "—"}</strong></div>
          <div><span>RSS FEEDS / ENTRIES</span><strong className="mono">{audit ? `${audit.summary.rss_feeds} / ${audit.summary.rss_entries}` : "—"}</strong></div>
        </div>
        <div className="audit-toolbar"><h2>Raw outputs</h2><span className="mono">{outputs.total} RESULTS</span></div>
        <div className="collection-filters">
          <input aria-label="Search outputs" placeholder="Search title, URL, or source" value={filters.q} onChange={event => { setPage(1); setFilters({ ...filters, q: event.target.value }); }} />
          <input aria-label="Filter by source" placeholder="Source" value={filters.source} onChange={event => { setPage(1); setFilters({ ...filters, source: event.target.value }); }} />
          <select aria-label="Filter output type" value={filters.type} onChange={event => { setPage(1); setFilters({ ...filters, type: event.target.value }); }}><option value="">All types</option><option value="SOURCE_ATTEMPT">Source attempts</option><option value="RSS_ENTRY">RSS entries</option></select>
          <select aria-label="Filter output status" value={filters.status} onChange={event => { setPage(1); setFilters({ ...filters, status: event.target.value }); }}><option value="">All statuses</option>{["COLLECTED", "FAILED", "ROBOTS_BLOCKED", "HTTP_FORBIDDEN", "HTTP_522"].map(value => <option key={value}>{value}</option>)}</select>
        </div>
        {outputs.items.length ? <div className="audit-list">{outputs.items.map(item => <details className="output-row" key={item.id}>
          <summary><strong>{item.title}<small>{item.source} · {item.type.replaceAll("_", " ")}</small></strong><span className={`audit-status ${item.status === "COLLECTED" ? "ok" : item.status === "ROBOTS_BLOCKED" ? "warn" : "bad"}`}>{item.status.replaceAll("_", " ")}</span><span className="mono">{item.http_status ?? "—"}</span><span>Details ↓</span></summary>
          <div className="output-detail"><dl>
            <dt>Source</dt><dd>{item.source}</dd><dt>Status</dt><dd>{item.status}{item.http_status ? ` · HTTP ${item.http_status}` : ""}</dd>
            {item.feed_url && <><dt>Feed URL</dt><dd>{item.feed_url}</dd></>}
            {item.entry_id && <><dt>Entry ID</dt><dd>{item.entry_id}</dd></>}
            {item.published && <><dt>Published</dt><dd>{item.published}</dd></>}
            {item.updated && <><dt>Updated</dt><dd>{item.updated}</dd></>}
            {item.author && <><dt>Author</dt><dd>{item.author}</dd></>}
            {item.tags?.length ? <><dt>Tags</dt><dd>{item.tags.join(", ")}</dd></> : null}
            {item.rss_type && <><dt>Feed type</dt><dd>{item.rss_type}</dd></>}
            {item.discovery_method && <><dt>Discovery</dt><dd>{item.discovery_method}</dd></>}
            {item.base_url && <><dt>Requested URL</dt><dd>{item.base_url}</dd></>}
            {item.final_url && <><dt>Final URL</dt><dd>{item.final_url}</dd></>}
            {item.content_type && <><dt>Content type</dt><dd>{item.content_type}</dd></>}
            {item.content_length !== undefined && <><dt>Bytes captured</dt><dd>{item.content_length.toLocaleString()}</dd></>}
            {item.sha256 && <><dt>SHA-256</dt><dd className="mono">{item.sha256}</dd></>}
            {item.robots_status && <><dt>Robots check</dt><dd>{item.robots_status}</dd></>}
            {item.duration_ms !== undefined && <><dt>Duration</dt><dd>{item.duration_ms} ms</dd></>}
            {item.feed_count !== undefined && <><dt>Feeds found</dt><dd>{item.feed_count}</dd></>}
            {(item.error || item.rss_error) && <><dt>Error</dt><dd>{[item.error_type, item.error, item.rss_error].filter(Boolean).join(": ")}</dd></>}
          </dl>{item.summary && <div className="extracted-summary"><strong>Extracted summary</strong><p>{item.summary}</p></div>}
          {item.url && /^https?:\/\//i.test(item.url) ? <a href={item.url} target="_blank" rel="noopener noreferrer">View source <ArrowUpRight size={12} /></a> : <span>Source link unavailable</span>}
          </div>
        </details>)}</div> : <div className="management-empty">No raw outputs match these filters.</div>}
        <div className="pagination"><button disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button><span className="mono">PAGE {page} / {pages}</span><button disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button></div>
        <div className="audit-toolbar"><h2>Collection jobs</h2><span className="mono">{jobs.length} RECENT</span></div>
        {jobs.length ? <div className="management-list">{jobs.map(job => <div key={job.id}><strong>{job.query}</strong><span>{job.status}</span><span className="mono">{job.attempts} attempts</span><span className="mono">{job.source_id.slice(0, 8)}</span></div>)}</div> : <div className="management-empty">No collection jobs stored yet.</div>}
      </>}
    </div></main>;
}
