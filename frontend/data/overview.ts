import type { LucideIcon } from "lucide-react";
import { Activity, Archive, BarChart3, Boxes, CalendarClock, Copy, Database, Download, FileText, Fingerprint, Globe2, Inbox, Layers, Link2, Network, Settings, ShieldCheck, Target, Users } from "lucide-react";
import type { OverviewMetrics } from "@/types/overview";

export const metricDefinitions: { key: keyof OverviewMetrics; label: string; icon: LucideIcon }[] = [
  { key: "sources", label: "Total sources", icon: Database },
  { key: "raw_evidence", label: "Raw evidence", icon: Inbox },
  { key: "canonical_records", label: "Canonical records", icon: Layers },
  { key: "unique_evidence", label: "Unique evidence", icon: Fingerprint },
  { key: "duplicates", label: "Duplicates", icon: Copy },
  { key: "active_jobs", label: "Active jobs", icon: Activity },
];

export const navigation: { group: string; items: { label: string; icon: LucideIcon; href?: string }[] }[] = [
  { group: "MAIN", items: [
    { label: "Overview", icon: BarChart3, href: "/" },
    { label: "Investigations", icon: Target },
    { label: "Collections", icon: Archive, href: "/collection" },
    { label: "Evidence", icon: FileText },
    { label: "Deduplication", icon: Copy },
    { label: "Source Lineage", icon: Link2 },
    { label: "Entities", icon: Users },
    { label: "Events", icon: CalendarClock, href: "/graph#timeline" },
    { label: "Graph", icon: Network, href: "/graph" },
    { label: "Timeline", icon: CalendarClock, href: "/graph#timeline" },
    { label: "Watchlists", icon: ShieldCheck, href: "/watchlists" },
    { label: "System Pipeline", icon: Activity },
  ] },
  { group: "INTELLIGENCE", items: [
    { label: "Geospatial", icon: Globe2 },
    { label: "Reports", icon: FileText },
    { label: "Exports", icon: Download },
  ] },
  { group: "ADMIN", items: [
    { label: "Data Sources", icon: Database },
    { label: "Integrations", icon: Boxes },
    { label: "User Management", icon: Users },
    { label: "Settings", icon: Settings },
  ] },
];

export const mapLayers = ["Interactive tiles", "Watchlist locations", "Coordinate grid"] as const;
