import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { MapPin } from "lucide-react";
import type { SourceMap, WatchlistSummary } from "@/types/overview";
import { getSourceMap, tokenKey } from "@/lib/api";

const LeafletMap = dynamic(() => import("@/components/map/LeafletMap"), { ssr: false });
export type MapStyle = "dark" | "street" | "satellite";

interface Props { watchlists: WatchlistSummary[]; selectedId: string | null; selectedLocationId?: string | null }

export function OperationalMap({ watchlists, selectedId, selectedLocationId }: Props) {
  const router = useRouter();
  const [style, setStyle] = useState<MapStyle>("dark");
  const [reports, setReports] = useState<SourceMap | null>(null);
  useEffect(() => {
    const token = sessionStorage.getItem(tokenKey);
    if (!token) return;
    let active = true;
    const refresh = () => getSourceMap(token).then(value => { if (active) setReports(value); }).catch(() => {});
    refresh();
    const timer = window.setInterval(refresh, 30000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  const markers = watchlists.flatMap(watchlist => watchlist.locations
    .filter(location => location.latitude !== null && location.longitude !== null)
    .map(location => ({ ...location, watchlist })));
  const selected = markers.find(marker => marker.id === selectedLocationId) ?? markers.find(marker => marker.watchlist.id === selectedId);

  return <section className="panel map-panel" aria-label="Geospatial overview">
    <div className="panel-header"><div><span className="panel-kicker">01 / GEOSPATIAL</span><h2>Operational map</h2></div><div className="panel-meta mono">{markers.length} WATCHLIST LOCATIONS · {reports?.items.length ?? 0} UNVALIDATED CITY MENTIONS</div></div>
    <div className="map-canvas-container">
      <LeafletMap watchlists={watchlists} reports={reports?.items ?? []} selectedId={selectedId} selectedLocationId={selectedLocationId} tileStyle={style} onOpen={(watchlistId, locationId) => void router.push(`/incidents/${encodeURIComponent(watchlistId)}?location=${encodeURIComponent(locationId)}`)} />
      <div className="map-style-switcher" role="group" aria-label="Map appearance">{(["dark", "street", "satellite"] as const).map(option => <button key={option} aria-pressed={style === option} onClick={() => setStyle(option)}>{option === "street" ? "Streets" : option === "satellite" ? "Satellite" : "Dark"}</button>)}</div>
      {!markers.length && <div className="map-empty"><MapPin size={21} /><strong>No georeferenced watchlist locations</strong><span>Add coordinates to a watchlist to place it on the map.</span></div>}
      {selected && <div className="map-selection"><span className="eyebrow">SELECTED LOCATION</span><strong>{selected.name}</strong><span>{selected.watchlist.title}</span><code>{selected.latitude?.toFixed(4)}°, {selected.longitude?.toFixed(4)}°</code></div>}
      {reports && <div className="map-report-legend">◉ {reports.items.length} approximate headline city mentions · {reports.unmapped_entries} reports without a mapped city · <Link href="/collection">View all raw output</Link></div>}
    </div>
  </section>;
}
