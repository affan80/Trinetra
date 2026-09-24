import { useState } from "react";
import { Crosshair, Layers3, MapPin, Minus, Plus } from "lucide-react";
import { mapLayers } from "@/data/overview";
import type { WatchlistSummary } from "@/types/overview";

interface Props {
  watchlists: WatchlistSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function OperationalMap({ watchlists, selectedId, onSelect }: Props) {
  const [enabled, setEnabled] = useState<Record<string, boolean>>({ Grid: true, "Watchlist locations": true });
  const [layersOpen, setLayersOpen] = useState(true);
  const [zoom, setZoom] = useState(1);
  const markers = watchlists.flatMap(watchlist => watchlist.locations
    .filter(location => location.latitude !== null && location.longitude !== null)
    .map(location => ({ ...location, watchlist })));
  const selected = markers.find(marker => marker.watchlist.id === selectedId);

  return <section className="panel map-panel" aria-label="Geospatial overview">
    <div className="panel-header"><div><span className="panel-kicker">01 / GEOSPATIAL</span><h2>Operational map</h2></div><div className="panel-meta mono">{markers.length} GEOREFERENCED LOCATIONS</div></div>
    <div className={`map-canvas ${enabled.Grid ? "show-grid" : ""}`}>
      <div className="map-axes"><span>90° N</span><span>0°</span><span>90° S</span></div>
      <div className="map-longitudes"><span>180° W</span><span>90° W</span><span>0°</span><span>90° E</span><span>180° E</span></div>
      <div className="map-toolbox">
        <button aria-label="Zoom in" title="Zoom in" onClick={() => setZoom(Math.min(2, zoom + 0.25))}><Plus size={15} /></button>
        <button aria-label="Zoom out" title="Zoom out" onClick={() => setZoom(Math.max(1, zoom - 0.25))}><Minus size={15} /></button>
        <button aria-label="Recenter" title="Recenter" onClick={() => setZoom(1)}><Crosshair size={15} /></button>
        <button aria-label="Toggle layers" title="Toggle layers" onClick={() => setLayersOpen(!layersOpen)}><Layers3 size={15} /></button>
      </div>
      <div className="map-plot" style={{ transform: `scale(${zoom})` }}>
        {enabled["Watchlist locations"] && markers.map(marker => <button
          key={`${marker.watchlist.id}:${marker.id}`}
          className={`map-marker ${marker.watchlist.id === selectedId ? "selected" : ""}`}
          style={{ left: `${(marker.longitude! + 180) / 360 * 100}%`, top: `${(90 - marker.latitude!) / 180 * 100}%` }}
          onClick={() => onSelect(marker.watchlist.id)}
          title={`${marker.name} · ${marker.watchlist.title}`}
          aria-label={`Select ${marker.name}`}
        ><MapPin size={18} fill="currentColor" /></button>)}
      </div>
      {layersOpen && <div className="map-layers"><div className="mini-heading">DISPLAY LAYERS</div>{mapLayers.map(layer => <label key={layer}><input type="checkbox" checked={enabled[layer]} onChange={event => setEnabled({ ...enabled, [layer]: event.target.checked })} />{layer}</label>)}</div>}
      {selected && <div className="map-selection"><span className="eyebrow">SELECTED LOCATION</span><strong>{selected.name}</strong><span>{selected.watchlist.title}</span><code>{selected.latitude?.toFixed(4)}°, {selected.longitude?.toFixed(4)}°</code></div>}
      {markers.length === 0 && <div className="map-empty"><MapPin size={21} /><strong>No georeferenced watchlist locations</strong><span>Add coordinates to a watchlist to place it on the map.</span></div>}
      <div className="map-disclaimer">COORDINATE GRID · NO BASEMAP LOADED</div>
    </div>
  </section>;
}
