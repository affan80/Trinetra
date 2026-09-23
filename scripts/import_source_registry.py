#!/usr/bin/env python3
"""Build the canonical Layer 3 source manifest from Markdown links."""
import argparse
import json
import re
import uuid
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import yaml

TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid", "mc_cid", "mc_eid"}
SECTOR_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
LINK_RE = re.compile(r"\[([^]]+)\]\((https?://[^)\s]+)\)")

def canonical_url(value: str) -> str:
    parts = urlsplit(value.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING])
    path = parts.path or "/"
    if path != "/": path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))

def canonical_host(hostname: str) -> str:
    host = hostname.lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host

def allowed_domains(hostname: str) -> list[str]:
    host = hostname.lower().rstrip(".")
    root = canonical_host(host)
    return list(dict.fromkeys([host, root, f"www.{root}"]))

def source_id(hostname: str, path: str = "/") -> str:
    suffix = "" if path in {"", "/"} else "-" + re.sub(r"[^A-Z0-9]+", "-", path.upper()).strip("-")
    return ("SRC-" + re.sub(r"[^A-Z0-9]+", "-", hostname.upper()).strip("-") + suffix)[:60].rstrip("-")

def preferred_adapter(sector: str, name: str) -> tuple[str, str, bool]:
    sector = sector.upper()
    if sector == "NEWS": return "RSS", "WEB", True
    if sector in {"BLOG_ANALYSIS", "GOVERNMENT"}: return "RSS", "WEB", True
    if "TEST" in sector: return "WEB", "WEB", False
    return "WEB", "WEB", False

def parse_document(path: Path) -> tuple[list[dict], int, int]:
    records = {}
    missing = 0
    parsed = 0
    sector = "UNCLASSIFIED"
    for line in path.read_text(encoding="utf-8").splitlines():
        heading = SECTOR_RE.match(line)
        if heading:
            sector = heading.group(1).strip().upper().replace(" ", "_")
            continue
        match = LINK_RE.search(line)
        if not match:
            if line.lstrip().startswith("- [") and "http" not in line: missing += 1
            continue
        name, raw_url = match.groups()
        parsed += 1
        url = canonical_url(raw_url)
        host = urlsplit(url).hostname
        if not host: continue
        host = canonical_host(host)
        key = (host, urlsplit(url).path or "/")
        preferred, fallback, discover = preferred_adapter(sector, name)
        row = records.setdefault(key, {"id": source_id(host, urlsplit(url).path), "name": name.strip(), "sector": [], "source_class": "NEWS" if sector == "NEWS" else "BLOG" if sector == "BLOG_ANALYSIS" else "GOVERNMENT" if sector == "GOVERNMENT" else "OTHER", "base_url": url, "allowed_domains": allowed_domains(host), "enabled": True, "preferred_adapter": preferred, "fallback_adapter": fallback, "language": ["en"], "country": [], "priority": "MEDIUM", "discover_rss": discover, "robots_policy": "CHECK", "auth_type": "NONE"})
        row["allowed_domains"] = list(dict.fromkeys(row["allowed_domains"] + allowed_domains(host)))
        if sector not in row["sector"]: row["sector"].append(sector)
    return list(records.values()), missing, parsed

def write_manifest(records: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump({"sources": records}, sort_keys=False), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("document", nargs="?", default="docs/source_registry.md"); parser.add_argument("--output", default="config/source_registry.yaml"); parser.add_argument("--seed", action="store_true")
    args = parser.parse_args(); records, missing, parsed = parse_document(Path(args.document)); write_manifest(records, Path(args.output))
    print(f"Parsed: {parsed}"); print(f"Unique canonical sources: {len(records)}"); print(f"Duplicates merged: {max(0, parsed - len(records))}"); print(f"Invalid/missing URLs: {missing}")
    if args.seed:
        from backend.app.db.database import SessionLocal
        from backend.app.db.models import Source
        db = SessionLocal()
        try:
            for row in records:
                existing = db.query(Source).filter(Source.name == row["name"]).first()
                values = {"name": row["name"], "source_class": row["source_class"], "adapter_name": row["preferred_adapter"].lower(), "enabled": row["enabled"], "allowed_domains": row["allowed_domains"], "config": {"base_url": row["base_url"], "discover_rss": row["discover_rss"]}}
                if existing: [setattr(existing, key, value) for key, value in values.items() if key != "name"]
                else: db.add(Source(**values))
            db.commit()
        finally: db.close()

if __name__ == "__main__": main()
