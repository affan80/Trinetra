import feedparser
from backend.app.security.http_client import fetch

def collect(feed_url: str, allowed_domains: list[str], checkpoint: dict | None = None) -> dict:
    checkpoint = checkpoint or {}; headers = {}
    if checkpoint.get("etag"): headers["If-None-Match"] = checkpoint["etag"]
    if checkpoint.get("last_modified"): headers["If-Modified-Since"] = checkpoint["last_modified"]
    response = fetch(feed_url, allowed_domains, headers=headers, max_bytes=10 * 1024 * 1024)
    parsed = feedparser.parse(response.body)
    if parsed.bozo and not parsed.entries: raise ValueError("INVALID_RSS")
    entries = [{"entry_id": e.get("id") or e.get("link"), "title": e.get("title"), "url": e.get("link"), "published": e.get("published"), "updated": e.get("updated"), "author": e.get("author"), "tags": [t.get("term") for t in e.get("tags", [])], "summary": e.get("summary")} for e in parsed.entries]
    after = {"etag": response.headers.get("etag"), "last_modified": response.headers.get("last-modified"), "last_seen_entry_id": entries[0]["entry_id"] if entries else checkpoint.get("last_seen_entry_id"), "last_seen_timestamp": entries[0].get("published") if entries else checkpoint.get("last_seen_timestamp")}
    return {"requested_url": response.requested_url, "final_url": response.final_url, "status_code": response.status_code, "content_type": response.content_type, "body": response.body, "redirect_chain": response.redirect_chain, "entries": entries, "checkpoint_before": checkpoint, "checkpoint_after": after, "headers": response.headers}
