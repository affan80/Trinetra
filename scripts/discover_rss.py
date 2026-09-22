#!/usr/bin/env python3
import argparse
from pathlib import Path
import yaml
from backend.app.services.rss_discovery import discover

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--source"); parser.add_argument("--sector"); parser.add_argument("--all-enabled", action="store_true"); parser.add_argument("--limit", type=int, default=20); parser.add_argument("--manifest", default="config/source_registry.yaml")
    args = parser.parse_args(); sources = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8"))["sources"]
    selected = [s for s in sources if s.get("enabled") and s.get("discover_rss") and (args.source is None or s["id"] == args.source) and (args.sector is None or args.sector.upper() in s.get("sector", []))]
    if not args.all_enabled and args.source is None and args.sector is None: selected = selected[:args.limit]
    for source in selected:
        try:
            feeds = discover(source["base_url"], [d for d in source.get("allowed_domains", []) if d])
            print(source["id"], feeds)
        except (OSError, ValueError) as exc:
            print(source["id"], "ERROR", str(exc))

if __name__ == "__main__": main()
