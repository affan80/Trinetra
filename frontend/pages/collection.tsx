import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getSourceAudit, request, tokenKey } from "@/lib/api";
import type { SourceAudit } from "@/types/overview";

interface Job { id: string; query: string; status: string; attempts: number; source_id: string }

export default function Collection() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [audit, setAudit] = useState<SourceAudit | null>(null);
  const [filter, setFilter] = useState("All");
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = sessionStorage.getItem(tokenKey);
    if (!token) { queueMicrotask(() => setReady(true)); return; }
    let active = true;
    const update = async () => {
      try {
        const [nextJobs, nextAudit] = await Promise.all([request<Job[]>("collection-jobs", token), getSourceAudit(token)]);
        if (active) { setJobs(nextJobs); setAudit(nextAudit); setError(""); }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Collection status unavailable");
      } finally {
        if (active) setReady(true);
      }
    };
    void update();
    const interval = window.setInterval(() => void update(), 3_000);
    return () => { active = false; window.clearInterval(interval); };
  }, []);

  const visibleSources = audit?.sources.filter(source => filter === "All" ||
    (filter === "Collected" && source.status === "COLLECTED") ||
    (filter === "Failed" && (source.status === "FAILED" || source.status === "HTTP_FORBIDDEN")) ||
    (filter === "Blocked" && source.status === "ROBOTS_BLOCKED")) ?? [];

  return <main className="management-page"><div className="management-bar"><Link href="/"><ArrowLeft size={15} /> Overview</Link><strong>TRINETRA / COLLECTIONS</strong></div>
    <div className="management-content"><span className="eyebrow">COLLECTION PIPELINE</span><h1>Source collection</h1><p>Live registry audit and collection jobs. Captures are raw observations, not verified intelligence.</p>
      {error && <div className="form-error" role="alert">{error}</div>}
      {!ready ? <p>Loading…</p> : !sessionStorage.getItem(tokenKey) ? <p>Sign in on the <Link href="/">overview</Link> to view collection status.</p> : <>
        <div className="audit-summary">
          <div><span>SCAN STATUS</span><strong>{audit?.status.replaceAll("_", " ") ?? "UNAVAILABLE"}</strong></div>
          <div><span>PROGRESS</span><strong className="mono">{audit ? `${audit.summary.completed} / ${audit.summary.total}` : "—"}</strong></div>
          <div><span>CAPTURED</span><strong className="mono">{audit?.summary.collected ?? "—"}</strong></div>
          <div><span>FAILED / BLOCKED</span><strong className="mono">{audit ? `${audit.summary.failed} / ${audit.summary.blocked}` : "—"}</strong></div>
          <div><span>RSS FEEDS / ENTRIES</span><strong className="mono">{audit ? `${audit.summary.rss_feeds} / ${audit.summary.rss_entries}` : "—"}</strong></div>
        </div>
        <div className="audit-toolbar"><h2>Registry sources</h2><span className="mono">{audit?.updated_at ? `UPDATED ${new Date(audit.updated_at).toISOString().slice(0, 19).replace("T", " ")} UTC` : "AWAITING SCAN"}</span><select aria-label="Filter source status" value={filter} onChange={event => setFilter(event.target.value)}>{["All", "Collected", "Failed", "Blocked"].map(value => <option key={value}>{value}</option>)}</select></div>
        {visibleSources.length ? <div className="audit-list">{visibleSources.map(source => <div className="audit-row" key={source.id}>
          <strong>{source.name}<small>{source.base_url}</small></strong>
          <span className={`audit-status ${source.status === "COLLECTED" ? "ok" : source.status === "FAILED" ? "bad" : "warn"}`}>{source.status.replaceAll("_", " ")}</span>
          <span className="mono">{source.http_status ?? "—"}</span>
          <span className="mono">{source.content_length ? `${(source.content_length / 1024).toFixed(0)} KB` : "—"}</span>
          <span className="mono">{source.feeds?.reduce((sum, feed) => sum + (feed.entries ?? 0), 0) ?? 0} RSS ITEMS</span>
          {(source.error || source.feeds?.some(feed => feed.status === "FAILED")) && <small className="audit-error">{source.error || source.feeds?.find(feed => feed.status === "FAILED")?.rss_url + " feed failed"}</small>}
        </div>)}</div> : <div className="management-empty">{audit?.status === "RUNNING" ? "Scan is running; results will appear here as sources finish." : "No registry scan results yet."}</div>}
        <div className="audit-toolbar"><h2>Collection jobs</h2><span className="mono">{jobs.length} RECENT</span></div>
        {jobs.length ? <div className="management-list">{jobs.map(job => <div key={job.id}><strong>{job.query}</strong><span>{job.status}</span><span className="mono">{job.attempts} attempts</span><span className="mono">{job.source_id.slice(0, 8)}</span></div>)}</div> : <div className="management-empty">No collection jobs stored yet.</div>}
      </>}
    </div></main>;
}
