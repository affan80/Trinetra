export interface OverviewMetrics {
  sources: number;
  raw_evidence: number;
  canonical_records: number;
  unique_evidence: number;
  duplicates: number;
  active_jobs: number;
}

export interface WatchlistLocation {
  id: string;
  name: string;
  latitude: number | null;
  longitude: number | null;
}

export interface WatchlistSummary {
  id: string;
  title: string;
  objective: string;
  priority: string;
  status: string;
  updated_at: string;
  locations: WatchlistLocation[];
  record_count: number;
  source_count: number;
}

export interface EvidenceRecord {
  id: string;
  evidence_id: string;
  title: string;
  type: string;
  source: string;
  watchlist_id: string | null;
  timestamp: string;
  quality_score: number | null;
  quality_status: string | null;
  url: string | null;
}

export interface SourceSummary {
  id: string;
  name: string;
  category: string;
  enabled: boolean;
  health: string;
}

export interface SourceAudit {
  status: "NOT_STARTED" | "RUNNING" | "COMPLETE";
  started_at: string | null;
  updated_at: string | null;
  summary: {
    total: number;
    completed: number;
    collected: number;
    failed: number;
    blocked: number;
    forbidden: number;
    skipped: number;
    rss_feeds: number;
    rss_entries: number;
  };
  sources: {
    id: string;
    name: string;
    base_url: string;
    status: string;
    http_status?: number;
    content_length?: number;
    duration_ms?: number;
    error?: string;
    feeds?: { rss_url: string; status: string; entries?: number; sample?: { title: string; url: string }[] }[];
  }[];
}

export interface TimelineEntry {
  id: string;
  timestamp: string;
  title: string;
  detail: string;
  kind: "evidence" | "job" | "audit";
}

export interface PipelineSummary {
  sources_enabled: number;
  sources_total: number;
  sources_unhealthy: number;
  workers_live: number;
  workers_total: number;
  jobs_failed: number;
  jobs_active: number;
  raw_stored: number;
  canonical_ready: number;
}

export interface Overview {
  generated_at: string;
  metrics: OverviewMetrics;
  watchlists: WatchlistSummary[];
  records: EvidenceRecord[];
  sources: SourceSummary[];
  timeline: TimelineEntry[];
  pipeline: PipelineSummary;
}

export interface Lineage {
  record: { id: string; title: string };
  source: { id: string; name: string; category: string } | null;
  raw: { id: string; retrieved_at: string } | null;
  related: { id: string; title: string; source: string }[];
  watchlist: { id: string; name: string } | null;
}
