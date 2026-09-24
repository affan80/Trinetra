#!/usr/bin/env python3
"""Collect every enabled registry base URL and write a bounded audit report."""

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import yaml

from backend.app.collectors.adapters.rss import collect as collect_rss
from backend.app.collectors.adapters.web import collect as collect_web
from backend.app.security.http_client import sha256
from backend.app.services.object_store import ObjectStore
from backend.app.services.rss_discovery import discover

USER_AGENT = "TRINETRA-OSINT-Collector/0.1"
RETRYABLE_ERRORS = {"gaierror", "ConnectError", "ConnectTimeout", "ReadTimeout", "ReadError", "WriteError", "RemoteProtocolError"}
RETRYABLE_STATUS = {500, 502, 503, 504}


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


@lru_cache(maxsize=512)
def _robots_rules(origin: str, domains: tuple[str, ...]):
    response = fetch_with_retry(urljoin(origin, "/robots.txt"), list(domains), max_bytes=1024 * 1024)
    if response.status_code == 429 or response.status_code >= 500:
        return None, f"HTTP_{response.status_code}", False
    if response.status_code >= 400:
        return None, f"HTTP_{response.status_code}", True
    parser = RobotFileParser()
    parser.parse(response.body.decode("utf-8", errors="ignore").splitlines())
    return parser, "CHECKED", False


def check_robots(url: str, domains: list[str]) -> tuple[bool, str]:
    parts = urlsplit(url)
    parser, status, allowed_without_rules = _robots_rules(f"{parts.scheme}://{parts.netloc}", tuple(domains))
    return (parser.can_fetch(USER_AGENT, url) if parser else allowed_without_rules), status


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
        if include_rss and status == "COLLECTED" and source.get("discover_rss"):
            row["feeds"] = []
            try:
                feeds = discover(row["base_url"], domains,
                                 allowed_url=lambda url: check_robots(url, domains)[0], home_body=response.body)
            except Exception as exc:
                row["rss_error"] = f"{type(exc).__name__}: {exc}"
                feeds = []
            for feed in feeds:
                try:
                    allowed, _ = check_robots(feed["rss_url"], domains)
                    if not allowed:
                        row["feeds"].append({**feed, "status": "ROBOTS_BLOCKED"})
                        continue
                    result = collect_rss(feed["rss_url"], domains)
                    feed_digest = sha256(result["body"])
                    row["feeds"].append({
                        **feed,
                        "status": "COLLECTED",
                        "http_status": result["status_code"],
                        "entries": len(result["entries"]),
                        "items": result["entries"],
                        "checkpoint_after": result["checkpoint_after"],
                        "sha256": feed_digest,
                        "raw_object_uri": store.put(result["body"], feed_digest),
                    })
                except Exception as exc:
                    row["feeds"].append({**feed, "status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
    except Exception as exc:
        row.update({"status": "FAILED", "error_type": type(exc).__name__, "error": str(exc)})
    row["duration_ms"] = round((time.monotonic() - started) * 1000)
    return row


def run_audit(sources: list[dict], store: ObjectStore, output: Path, workers: int, include_rss: bool) -> dict:
    """Write atomic progress snapshots so readers never see partial JSON."""
    output.parent.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict | None] = [None] * len(sources)

    def publish(status: str) -> dict:
        completed = [row for row in rows if row is not None]
        summary = {
            "total": len(sources),
            "completed": len(completed),
            "collected": sum(row["status"] == "COLLECTED" for row in completed),
            "failed": sum(row["status"] not in {"COLLECTED", "ROBOTS_BLOCKED", "HTTP_FORBIDDEN"}
                          and not row["status"].startswith("SKIPPED") and row["status"] != "MISSING_URL"
                          for row in completed),
            "blocked": sum(row["status"] == "ROBOTS_BLOCKED" for row in completed),
            "forbidden": sum(row["status"] == "HTTP_FORBIDDEN" for row in completed),
            "skipped": sum(row["status"].startswith("SKIPPED") or row["status"] == "MISSING_URL" for row in completed),
            "rss_feeds": sum(sum(feed.get("status") == "COLLECTED" for feed in row.get("feeds", [])) for row in completed),
            "rss_entries": sum(feed.get("entries", 0) for row in completed for feed in row.get("feeds", [])),
        }
        report = {"status": status, "started_at": started_at, "updated_at": datetime.now(timezone.utc).isoformat(),
                  "summary": summary, "sources": completed}
        pending = output.with_name(output.name + ".tmp")
        pending.write_text(json.dumps(report, indent=2), encoding="utf-8")
        os.replace(pending, output)
        return report

    report = publish("RUNNING")
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 16))) as pool:
        futures = {pool.submit(audit_source, source, store, include_rss): index for index, source in enumerate(sources)}
        for future in as_completed(futures):
            rows[futures[future]] = future.result()
            report = publish("RUNNING")
    return publish("COMPLETE")


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
    output = Path(args.output)
    report = run_audit(sources, ObjectStore(args.object_root), output, args.workers, args.rss)
    print(json.dumps(report["summary"], indent=2))
    print(f"Report: {output}")


if __name__ == "__main__":
    main()
