import { FormEvent, useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { request, tokenKey } from "@/lib/api";

export default function NewWatchlist() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [objective, setObjective] = useState("");
  const [priority, setPriority] = useState("MEDIUM");
  const [locationName, setLocationName] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = sessionStorage.getItem(tokenKey);
    if (!token) { setError("Sign in from the overview first."); return; }
    if ((latitude && !longitude) || (!latitude && longitude) || ((latitude || longitude) && !locationName)) {
      setError("Enter a location name and both coordinates, or leave all three blank.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await request("watchlists", token, {
        name, objective, priority,
        locations: locationName ? [{ name: locationName, latitude: latitude ? Number(latitude) : null, longitude: longitude ? Number(longitude) : null }] : [],
      });
      await router.push("/");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not create watchlist");
    } finally {
      setBusy(false);
    }
  }

  return <main className="management-page"><div className="management-bar"><Link href="/watchlists"><ArrowLeft size={15} /> Watchlists</Link><strong>TRINETRA / NEW WATCHLIST</strong></div>
    <div className="management-content narrow"><span className="eyebrow">MONITORING OBJECTIVE</span><h1>New watchlist</h1><p>The overview will show this watchlist and its location after saving.</p>
      <form className="management-form" onSubmit={submit}>
        <label>Name<input value={name} onChange={event => setName(event.target.value)} maxLength={200} required /></label>
        <label>Objective<textarea value={objective} onChange={event => setObjective(event.target.value)} rows={3} /></label>
        <label>Priority<select value={priority} onChange={event => setPriority(event.target.value)}>{["LOW", "MEDIUM", "HIGH", "CRITICAL"].map(value => <option key={value}>{value}</option>)}</select></label>
        <div className="mini-heading">OPTIONAL LOCATION</div>
        <label>Location name<input value={locationName} onChange={event => setLocationName(event.target.value)} /></label>
        <div className="form-pair"><label>Latitude<input type="number" step="any" min="-90" max="90" value={latitude} onChange={event => setLatitude(event.target.value)} /></label><label>Longitude<input type="number" step="any" min="-180" max="180" value={longitude} onChange={event => setLongitude(event.target.value)} /></label></div>
        {error && <div className="form-error" role="alert">{error}</div>}
        <button className="primary-button" disabled={busy}>{busy ? "Saving…" : "Create watchlist"}<ArrowRight size={15} /></button>
      </form>
    </div></main>;
}
