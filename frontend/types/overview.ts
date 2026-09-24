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
  demo: boolean;
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
  sources?: {
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

export interface SourceMap {
  total_entries: number;
  unmapped_entries: number;
  items: { id: string; title: string; source: string; city: string; latitude: number; longitude: number; published: string | null; url: string | null }[];
}

export interface RawCollectionOutput {
  id: string;
  type: "SOURCE_ATTEMPT" | "RSS_ENTRY";
  source_id: string;
  source: string;
  title: string;
  url: string | null;
  status: string;
  http_status: number | null;
  error?: string | null;
  published?: string | null;
  feed_url?: string;
  updated?: string | null;
  author?: string | null;
  summary?: string | null;
  tags?: string[];
  entry_id?: string | null;
  rss_type?: string;
  discovery_method?: string;
  base_url?: string;
  final_url?: string;
  content_type?: string;
  content_length?: number;
  sha256?: string;
  robots_status?: string;
  duration_ms?: number;
  error_type?: string;
  rss_error?: string;
  feed_count?: number;
}

export interface RawCollectionPage { items: RawCollectionOutput[]; total: number; page: number; size: number }

export interface IncidentContext {
  watchlist: { id: string; title: string; objective: string; status: string; priority: string; created_at: string; updated_at: string };
  locations: (WatchlistLocation & { country: string; region: string; city: string })[];
  selected_location_id: string | null;
  records: (EvidenceRecord & {
    source_id: string | null;
    published_at: string | null;
    retrieved_at: string | null;
    created_at: string;
    language: string | null;
    plain_text: string;
    content_blocks: unknown[];
    processing_quality: Record<string, unknown>;
    raw: {
      id: string; url: string | null; retrieved_at: string; source_url: string | null;
      http_status: number; content_type: string; content_length: number; sha256: string; adapter_type: string;
      provenance: { collector_id: string; collector_version: string; collection_method: string; requested_url: string | null; final_url: string | null; redirect_chain: unknown[]; observed_at: string } | null;
    } | null;
    clusters: { id: string; relationship: string; score: number }[];
  })[];
  timeline: TimelineEntry[];
}

export interface TimelineEntry {
  id: string;
  timestamp: string;
  title: string;
  detail: string;
  kind: "evidence" | "raw" | "job" | "audit";
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
