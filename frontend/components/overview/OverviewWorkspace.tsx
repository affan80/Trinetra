import { useCallback, useEffect, useState } from "react";
import { LoginPanel } from "@/components/auth/LoginPanel";
import { RecentEvidenceTable } from "@/components/evidence/RecentEvidenceTable";
import { SourceLineageGraph } from "@/components/graph/SourceLineageGraph";
import { ActiveInvestigationPanel } from "@/components/investigation/ActiveInvestigationPanel";
import { OperationalMap } from "@/components/map/OperationalMap";
import { PipelineHealth } from "@/components/pipeline/PipelineHealth";
import { AppShell } from "@/components/shell/AppShell";
import { OperationalTimeline } from "@/components/timeline/OperationalTimeline";
import { OperationalMetrics } from "@/components/overview/OperationalMetrics";
import { getLineage, getOverview, getSourceAudit, getSourceOutputs, tokenKey } from "@/lib/api";
import type { Lineage, Overview, RawCollectionOutput, SourceAudit } from "@/types/overview";

export function OverviewWorkspace() {
  const [token, setToken] = useState<string | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [audit, setAudit] = useState<SourceAudit | null>(null);
  const [rawOutputs, setRawOutputs] = useState<RawCollectionOutput[]>([]);
  const [lineage, setLineage] = useState<Lineage | null>(null);
  const [lineageError, setLineageError] = useState(false);
  const [selectedWatchlistId, setSelectedWatchlistId] = useState<string | null>(null);
  const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const pending = window.setTimeout(() => setToken(sessionStorage.getItem(tokenKey)), 0);
    return () => window.clearTimeout(pending);
  }, []);

  const refresh = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await getOverview(token);
      if (sessionStorage.getItem(tokenKey) !== token) return;
      setOverview(data);
      setSelectedWatchlistId(current => current && data.watchlists.some(item => item.id === current)
        ? current : data.watchlists[0]?.id ?? null);
      setSelectedRecordId(current => current && data.records.some(item => item.id === current)
        ? current : data.records[0]?.id ?? null);
      setError("");
    } catch (cause) {
      setOverview(null);
      if (cause instanceof Error && /401|Authentication|token/i.test(cause.message)) {
        sessionStorage.removeItem(tokenKey);
        setToken(null);
      }
      setError(cause instanceof Error ? cause.message : "Overview unavailable");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    const pending = window.setTimeout(() => void refresh(), 0);
    const interval = window.setInterval(() => void refresh(), 10_000);
    return () => { window.clearTimeout(pending); window.clearInterval(interval); };
  }, [refresh]);
  useEffect(() => {
    if (!token) return;
    let active = true;
    let timer = 0;
    const update = () => Promise.all([getSourceAudit(token), getSourceOutputs(token, "type=RSS_ENTRY&size=100"), getSourceOutputs(token, "type=SOURCE_ATTEMPT&size=100")]).then(([data, entries, attempts]) => {
      const seenSources = new Set<string>();
      const seenStatuses = new Set<string>();
      const acrossSources = entries.items.filter(item => !seenSources.has(item.source_id) && !!seenSources.add(item.source_id));
      const acrossStatuses = attempts.items.filter(item => !seenStatuses.has(item.status) && !!seenStatuses.add(item.status));
      if (active) { setAudit(data); setRawOutputs([...acrossSources, ...acrossStatuses]); timer = window.setTimeout(update, data.status === "RUNNING" ? 3_000 : 15_000); }
    }).catch(() => { if (active) { setAudit(null); setRawOutputs([]); timer = window.setTimeout(update, 15_000); } });
    void update();
    return () => { active = false; window.clearTimeout(timer); };
  }, [token]);
  useEffect(() => {
    if (!token || !selectedRecordId) return;
    let current = true;
    getLineage(selectedRecordId, token).then(data => {
      if (current) { setLineage(data); setLineageError(false); }
    }).catch(() => { if (current) { setLineage(null); setLineageError(true); } });
    return () => { current = false; };
  }, [selectedRecordId, token]);

  function signOut() {
    sessionStorage.removeItem(tokenKey);
    setToken(null);
    setOverview(null);
    setAudit(null);
    setLineage(null);
  }

  if (!token) return <LoginPanel onAuthenticated={value => {
    sessionStorage.setItem(tokenKey, value);
    setToken(value);
  }} />;

  const selectedWatchlist = overview?.watchlists.find(item => item.id === selectedWatchlistId) ?? null;
  const selectedRecord = overview?.records.find(item => item.id === selectedRecordId) ?? null;
  const visibleRecords = overview?.records.filter(record =>
    `${record.title} ${record.source} ${record.id}`.toLowerCase().includes(query.toLowerCase())) ?? [];

  return (
    <AppShell
      generatedAt={overview?.generated_at ?? null}
      query={query}
      onQueryChange={setQuery}
      onRefresh={refresh}
      onSignOut={signOut}
      loading={loading}
    >
      {error && <div className="error-banner" role="alert">{error} <button onClick={refresh}>Retry</button></div>}
      <div className="overview-heading">
        <div><span className="eyebrow">OPERATIONAL WORKSPACE / OVERVIEW</span><h1>Intelligence overview</h1></div>
        <div className="heading-note">LIVE DATABASE <span className="heading-dot" /> {overview ? "CONNECTED" : "CONNECTING"}</div>
      </div>
      <OperationalMetrics metrics={overview?.metrics ?? null} />
      <div className="primary-grid">
        <OperationalMap watchlists={overview?.watchlists ?? []} selectedId={selectedWatchlistId} />
        <ActiveInvestigationPanel watchlist={selectedWatchlist} records={overview?.records ?? []} />
      </div>
      <div className="lower-grid">
        <RecentEvidenceTable records={visibleRecords} rawOutputs={rawOutputs} selectedId={selectedRecordId} onSelect={setSelectedRecordId} />
        <SourceLineageGraph lineage={lineage?.record.id === selectedRecordId ? lineage : null} selectedRecord={selectedRecord} error={lineageError} />
        <OperationalTimeline entries={overview?.timeline ?? []} generatedAt={overview?.generated_at ?? null} />
        <PipelineHealth pipeline={overview?.pipeline ?? null} sources={overview?.sources ?? []} audit={audit} />
      </div>
    </AppShell>
  );
}
