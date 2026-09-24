import { metricDefinitions } from "@/data/overview";
import type { OverviewMetrics } from "@/types/overview";

export function OperationalMetrics({ metrics }: { metrics: OverviewMetrics | null }) {
  return <section className="metrics" aria-label="Operational metrics">
    {metricDefinitions.map(({ key, label, icon: Icon }) => <div className="metric-card" key={key}>
      <div className="metric-label"><Icon size={15} strokeWidth={1.7} /><span>{label}</span></div>
      <div className="metric-value mono">{metrics ? metrics[key].toLocaleString() : "—"}</div>
      <div className="metric-foot">{metrics ? "CURRENT TOTAL" : "AWAITING API"}</div>
    </div>)}
  </section>;
}
