import { useEffect, useMemo, useRef } from "react";
import L from "leaflet";
import type { SourceMap, WatchlistSummary } from "@/types/overview";
import type { MapStyle } from "@/components/map/OperationalMap";

const tiles: Record<MapStyle, { url: string; attribution: string; maxZoom: number }> = {
  dark: { url: "/api/map-tile/dark/{z}/{x}/{y}.png", attribution: '&copy; OpenStreetMap France &copy; OpenStreetMap contributors', maxZoom: 18 },
  street: { url: "/api/map-tile/street/{z}/{x}/{y}.png", attribution: '&copy; OpenStreetMap France &copy; OpenStreetMap contributors', maxZoom: 18 },
  satellite: { url: "/api/map-tile/satellite/{z}/{x}/{y}.jpg", attribution: 'Tiles &copy; Esri', maxZoom: 18 },
};

interface Props {
  watchlists: WatchlistSummary[];
  reports: SourceMap["items"];
  selectedId: string | null;
  selectedLocationId?: string | null;
  tileStyle: MapStyle;
  onOpen: (watchlistId: string, locationId: string) => void;
}

export default function LeafletMap({ watchlists, reports, selectedId, selectedLocationId, tileStyle, onOpen }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerLayerRef = useRef<L.LayerGroup | null>(null);
  const reportLayerRef = useRef<L.LayerGroup | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const onOpenRef = useRef(onOpen);
  const markerSignatureRef = useRef("");
  const centeredSelectionRef = useRef<string | null>(null);
  const reportFitRef = useRef(false);
  const markers = useMemo(() => watchlists.flatMap(watchlist => watchlist.locations
    .filter((location): location is typeof location & { latitude: number; longitude: number } => location.latitude !== null && location.longitude !== null)
    .map(location => ({ ...location, watchlist }))), [watchlists]);

  useEffect(() => { onOpenRef.current = onOpen; }, [onOpen]);
  useEffect(() => {
    if (!containerRef.current) return;
    const map = L.map(containerRef.current, { center: [25, 10], zoom: 2, minZoom: 2, maxZoom: 18 });
    markerLayerRef.current = L.layerGroup().addTo(map);
    reportLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; markerSignatureRef.current = ""; };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const previous = tileLayerRef.current;
    const next = L.tileLayer(tiles[tileStyle].url, tiles[tileStyle]);
    next.once("load", () => { if (previous && map.hasLayer(previous)) map.removeLayer(previous); });
    next.once("tileerror", () => { if (previous) { map.removeLayer(next); tileLayerRef.current = previous; } });
    tileLayerRef.current = next.addTo(map);
  }, [tileStyle]);

  useEffect(() => {
    const map = mapRef.current;
    const layer = markerLayerRef.current;
    if (!map || !layer) return;
    const signature = JSON.stringify([selectedId, selectedLocationId, markers.map(marker => [marker.id, marker.latitude, marker.longitude, marker.name, marker.watchlist.title, marker.watchlist.priority, marker.watchlist.record_count])]);
    if (markerSignatureRef.current === signature) return;
    markerSignatureRef.current = signature;
    layer.clearLayers();
    for (const marker of markers) {
      const icon = L.divIcon({
        className: "trinetra-leaflet-icon",
        html: `<div class="trinetra-custom-pin${(selectedLocationId ? marker.id === selectedLocationId : marker.watchlist.id === selectedId) ? " selected" : ""}"><span class="pin-radar"></span><span class="pin-head" aria-hidden="true">●</span></div>`,
        iconSize: [28, 28], iconAnchor: [14, 14],
      });
      const content = document.createElement("div");
      content.className = "map-popup-card";
      for (const [className, text] of [
        ["popup-badge", `${marker.watchlist.priority} PRIORITY`], ["popup-name", marker.name],
        ["popup-watchlist", marker.watchlist.title], ["popup-coords mono", `${marker.watchlist.record_count} linked records`],
        ["popup-action", "Open incident workspace"],
      ]) {
        const line = document.createElement("div"); line.className = className; line.textContent = text; content.append(line);
      }
      L.marker([marker.latitude, marker.longitude], { icon, keyboard: true, title: `Open ${marker.name} incident workspace`, alt: marker.name })
        .bindTooltip(content, { className: "trinetra-map-popup", direction: "top", offset: [0, -12] })
        .on("click", () => onOpenRef.current(marker.watchlist.id, marker.id))
        .addTo(layer);
    }
    if (markers.length && !selectedLocationId && map.getZoom() === 2) map.fitBounds(L.latLngBounds(markers.map(marker => [marker.latitude, marker.longitude])), { padding: [50, 50], maxZoom: 6 });
  }, [markers, selectedId, selectedLocationId]);

  useEffect(() => {
    const map = mapRef.current;
    const layer = reportLayerRef.current;
    if (!map || !layer) return;
    layer.clearLayers();
    const byCity = new Map<string, SourceMap["items"]>();
    for (const report of reports) byCity.set(report.city, [...(byCity.get(report.city) ?? []), report]);
    for (const [city, items] of byCity) {
      const first = items[0];
      const popup = document.createElement("div");
      popup.className = "map-report-popup";
      const heading = document.createElement("strong");
      heading.textContent = `${city} · ${items.length} unvalidated report${items.length === 1 ? "" : "s"}`;
      popup.append(heading);
      const note = document.createElement("p");
      note.textContent = "Approximate city mentioned in headline, not a verified incident site.";
      popup.append(note);
      for (const item of items) {
        const line = item.url ? document.createElement("a") : document.createElement("span");
        line.textContent = `${item.source}: ${item.title}`;
        if (item.url && line instanceof HTMLAnchorElement) {
          line.href = item.url;
          line.target = "_blank";
          line.rel = "noopener noreferrer";
        }
        popup.append(line);
      }
      L.circleMarker([first.latitude, first.longitude], { radius: 9, color: "#63c8d1", weight: 2, fillColor: "#123b43", fillOpacity: .85 })
        .bindTooltip(`${city}: ${items.length} unvalidated headline mention${items.length === 1 ? "" : "s"}`)
        .bindPopup(popup, { maxWidth: 320, className: "trinetra-report-popup" })
        .addTo(layer);
    }
    if (reports.length && !reportFitRef.current) {
      reportFitRef.current = true;
      map.fitBounds(L.latLngBounds([...markers.map(marker => [marker.latitude, marker.longitude] as [number, number]), ...reports.map(item => [item.latitude, item.longitude] as [number, number])]), { padding: [45, 45], maxZoom: 5 });
    }
  }, [reports, markers]);

  useEffect(() => {
    const selection = selectedLocationId;
    if (!selection || centeredSelectionRef.current === selection) return;
    const marker = markers.find(item => item.id === selectedLocationId);
    if (marker && mapRef.current) {
      mapRef.current.setView([marker.latitude, marker.longitude], Math.max(mapRef.current.getZoom(), 5));
      centeredSelectionRef.current = selection;
    }
  }, [markers, selectedLocationId]);

  return <div ref={containerRef} className={`leaflet-map-root ${tileStyle === "dark" ? "map-dark" : ""}`} />;
}
