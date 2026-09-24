import { Activity } from "lucide-react";
import Link from "next/link";
import type { PipelineSummary, SourceAudit, SourceSummary } from "@/types/overview";

interface Props { pipeline: PipelineSummary | null; sources: SourceSummary[]; audit: SourceAudit | null }

export function PipelineHealth({ pipeline, sources, audit }: Props) {
  const observed = pipeline && (pipeline.sources_total || pipeline.workers_total || pipeline.raw_stored || pipeline.canonical_ready);
  const alert = pipeline && (pipeline.sources_unhealthy > 0 || pipeline.jobs_failed > 0);
  const stages = pipeline ? [
    { label: "Source registry", value: `${pipeline.sources_enabled}/${pipeline.sources_total}`, state: pipeline.sources_unhealthy ? "warn" : "ok" },
    { label: "Collector workers", value: `${pipeline.workers_live}/${pipeline.workers_total}`, state: pipeline.workers_total && !pipeline.workers_live ? "warn" : "neutral" },
    { label: "Active jobs", value: String(pipeline.jobs_active), state: "neutral" },
    { label: "Raw objects", value: String(pipeline.raw_stored), state: "neutral" },
    { label: "Canonical records", value: String(pipeline.canonical_ready), state: "neutral" },
    { label: "Failed jobs", value: String(pipeline.jobs_failed), state: pipeline.jobs_failed ? "warn" : "ok" },
  ] : [];

  return <section className="panel pipeline-panel">
    <div className="panel-header"><div><span className="panel-kicker">06 / SYSTEM</span><h2>Pipeline health</h2></div><Activity size={15} /></div>
    <div className="pipeline-body">
      <div className={`pipeline-status ${alert ? "warn" : observed ? "ok" : "neutral"}`}><span className="status-dot" />{alert ? "Attention required" : observed ? "Pipeline observed" : "No pipeline activity recorded"}</div>
      <div className="pipeline-stage-list">{stages.map(stage => <div className="pipeline-stage" key={stage.label}><span>{stage.label}</span><strong className={`mono ${stage.state}`}>{stage.value}</strong></div>)}</div>
      <div className="audit-overview">
        <div className="mini-heading">SOURCE COLLECTION <Link href="/collection">VIEW ALL →</Link></div>
        <div className="pipeline-stage"><span>{audit?.status === "RUNNING" ? "Scan in progress" : audit?.status === "COMPLETE" ? "Last scan complete" : "Scan not started"}</span><strong className="mono">{audit ? `${audit.summary.completed}/${audit.summary.total}` : "—"}</strong></div>
        {audit && <><div className="pipeline-stage"><span>Captured / failed / blocked</span><strong className="mono">{audit.summary.collected} / {audit.summary.failed} / {audit.summary.blocked}</strong></div><div className="pipeline-stage"><span>RSS feeds / entries</span><strong className="mono">{audit.summary.rss_feeds} / {audit.summary.rss_entries}</strong></div></>}
      </div>
      <div className="pipeline-sources"><div className="mini-heading">SOURCE HEALTH</div>{sources.length ? sources.slice(0, 4).map(source => <div key={source.id}><span className={`source-dot ${source.health === "UNHEALTHY" ? "warn" : source.health === "HEALTHY" ? "ok" : "neutral"}`} />{source.name}<small>{source.health.toLowerCase()}</small></div>) : <p>No registered sources.</p>}</div>
      <div className="pipeline-foot">Only configured services with stored status are shown. Unmeasured stages are not marked healthy.</div>
    </div>
  </section>;
}
