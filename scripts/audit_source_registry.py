#!/usr/bin/env python3
"""Collect every enabled registry base URL and write a bounded audit report."""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import yaml

from backend.app.collectors.adapters.rss import collect as collect_rss
from backend.app.collectors.adapters.web import collect as collect_web
from backend.app.security.http_client import sha256
from backend.app.services.object_store import ObjectStore
from backend.app.services.rss_discovery import discover

USER_AGENT = "TRINETRA-OSINT-Collector/0.1"
RETRYABLE_ERRORS = {"gaierror", "ConnectError", "ConnectTimeout", "ReadTimeout", "ReadError", "WriteError", "RemoteProtocolError"}
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def fetch_with_retry(url: str, domains: list[str], max_bytes: int):
    for attempt in range(3):
        try:
            response = collect_web(url, domains, max_bytes=max_bytes)
            if response.status_code not in RETRYABLE_STATUS or attempt == 2:
                return response
        except Exception as exc:
            if type(exc).__name__ not in RETRYABLE_ERRORS or attempt == 2:
                raise
        time.sleep(0.5 * (attempt + 1))


def check_robots(base_url: str, domains: list[str]) -> tuple[bool, str]:
    response = fetch_with_retry(urljoin(base_url, "/robots.txt"), domains, max_bytes=1024 * 1024)
    if response.status_code == 429 or response.status_code >= 500:
        return False, f"HTTP_{response.status_code}"
    if response.status_code >= 400:
        return True, f"HTTP_{response.status_code}"
    parser = RobotFileParser()
    parser.parse(response.body.decode("utf-8", errors="ignore").splitlines())
    return parser.can_fetch(USER_AGENT, base_url), "CHECKED"


def audit_source(source: dict, store: ObjectStore, include_rss: bool = False) -> dict:
    started = time.monotonic()
    row = {"id": source.get("id"), "name": source.get("name"), "base_url": source.get("base_url")}
    if not source.get("enabled", False):
        return {**row, "status": "SKIPPED_DISABLED"}
    if not row["base_url"]:
        return {**row, "status": "MISSING_URL"}
    domains = [domain for domain in source.get("allowed_domains", []) if domain]
    try:
        allowed, robots_status = check_robots(row["base_url"], domains)
        if not allowed:
            return {**row, "status": "ROBOTS_BLOCKED", "robots_status": robots_status}
        response = fetch_with_retry(row["base_url"], domains, max_bytes=10 * 1024 * 1024)
        digest = sha256(response.body)
        status = "COLLECTED" if 200 <= response.status_code < 300 else "HTTP_FORBIDDEN" if response.status_code in {401, 403} else f"HTTP_{response.status_code}"
        row.update({
            "status": status,
            "final_url": response.final_url,
            "http_status": response.status_code,
            "content_type": response.content_type,
            "content_length": len(response.body),
            "sha256": digest,
            "raw_object_uri": store.put(response.body, digest),
            "robots_status": robots_status,
        })
        if include_rss and source.get("discover_rss"):
            row["feeds"] = []
            for feed in discover(row["base_url"], domains):
                result = collect_rss(feed["rss_url"], domains)
                feed_digest = sha256(result["body"])
                row["feeds"].append({
                    **feed,
                    "http_status": result["status_code"],
                    "entries": len(result["entries"]),
                    "sample": [{"title": item["title"], "url": item["url"]} for item in result["entries"][:3]],
                    "checkpoint_after": result["checkpoint_after"],
                    "sha256": feed_digest,
                    "raw_object_uri": store.put(result["body"], feed_digest),
                })
    except Exception as exc:
        row.update({"status": "FAILED", "error_type": type(exc).__name__, "error": str(exc)})
    row["duration_ms"] = round((time.monotonic() - started) * 1000)
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="config/source_registry.yaml")
    parser.add_argument("--output", default="artifacts/source_audit.json")
    parser.add_argument("--object-root", default="/tmp/trinetra-registry-evidence")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--rss", action="store_true")
    args = parser.parse_args()

    sources = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8")).get("sources", [])
    if args.limit is not None:
        sources = sources[:max(0, args.limit)]
    store = ObjectStore(args.object_root)
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 16))) as pool:
        rows = list(pool.map(lambda source: audit_source(source, store, args.rss), sources))
    summary = {
        "total": len(rows),
        "collected": sum(row["status"] == "COLLECTED" for row in rows),
        "failed": sum(row["status"] == "FAILED" for row in rows),
        "blocked": sum(row["status"] == "ROBOTS_BLOCKED" for row in rows),
        "forbidden": sum(row["status"] == "HTTP_FORBIDDEN" for row in rows),
        "skipped": sum(row["status"].startswith("SKIPPED") or row["status"] == "MISSING_URL" for row in rows),
        "rss_feeds": sum(len(row.get("feeds", [])) for row in rows),
        "rss_entries": sum(feed["entries"] for row in rows for feed in row.get("feeds", [])),
    }
    report = {"summary": summary, "sources": rows}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Report: {output}")


if __name__ == "__main__":
    main()
