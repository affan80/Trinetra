import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Plus } from "lucide-react";
import { request, tokenKey } from "@/lib/api";

interface WatchlistRow { id: string; name: string; status: string; priority: string; updated_at: string }

export default function Watchlists() {
  const [items, setItems] = useState<WatchlistRow[]>([]);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = sessionStorage.getItem(tokenKey);
    if (!token) { queueMicrotask(() => setReady(true)); return; }
    request<WatchlistRow[]>("watchlists", token).then(setItems).catch(cause => setError(cause.message)).finally(() => setReady(true));
  }, []);

  return <main className="management-page"><div className="management-bar"><Link href="/"><ArrowLeft size={15} /> Overview</Link><strong>TRINETRA / WATCHLISTS</strong></div>
    <div className="management-content"><span className="eyebrow">MONITORING OBJECTIVES</span><h1>Watchlists</h1><p>Watchlists connect collection plans, evidence, and georeferenced locations.</p>
      <Link href="/watchlists/new" className="management-create"><Plus size={15} /> New watchlist</Link>
      {error && <div className="form-error" role="alert">{error}</div>}
      {!ready ? <p>Loading…</p> : !sessionStorage.getItem(tokenKey) ? <p>Sign in on the <Link href="/">overview</Link> to view watchlists.</p> : items.length ? <div className="management-list">{items.map(item => <div key={item.id}><span className="status-dot on" /><strong>{item.name}</strong><span>{item.status}</span><span>{item.priority}</span><span className="mono">{new Date(item.updated_at).toISOString().slice(0, 16).replace("T", " ")} UTC</span></div>)}</div> : <div className="management-empty">No watchlists stored yet. Create one to begin monitoring.</div>}
    </div></main>;
}
