import { useState } from "react";
import { Clock3 } from "lucide-react";
import type { TimelineEntry } from "@/types/overview";

export function OperationalTimeline({ entries, generatedAt }: { entries: TimelineEntry[]; generatedAt: string | null }) {
  const [period, setPeriod] = useState("7 days");
  const cutoff = period === "All" || !generatedAt ? 0 : new Date(generatedAt).getTime() - (period === "48 hours" ? 48 : 168) * 60 * 60 * 1000;
  const visible = entries.filter(entry => new Date(entry.timestamp).getTime() >= cutoff);

  return <section className="panel timeline-panel">
    <div className="panel-header"><div><span className="panel-kicker">05 / CHRONOLOGY</span><h2>Timeline</h2></div><select aria-label="Timeline period" value={period} onChange={event => setPeriod(event.target.value)}><option>48 hours</option><option>7 days</option><option>All</option></select></div>
    <div className="panel-scroll timeline-list">{visible.length ? visible.map(entry => <div className={`timeline-entry ${entry.kind}`} key={entry.id}>
      <time className="mono" dateTime={entry.timestamp}>{new Date(entry.timestamp).toISOString().slice(5, 16).replace("T", " ")}</time>
      <div className="timeline-rail"><span /></div>
      <div><strong>{entry.title}</strong><small>{entry.detail}</small></div>
    </div>) : <div className="panel-empty"><Clock3 size={20} /><strong>No activity in this period</strong><span>Change the period or collect new evidence.</span></div>}</div>
  </section>;
}
