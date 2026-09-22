from pathlib import Path
from types import SimpleNamespace

from scripts.import_source_registry import canonical_url, parse_document
from backend.app.collectors.adapters import rss
from backend.app.security.http_client import sha256
from backend.app.security.network import resolve_public

FIXTURES = Path(__file__).parent / "fixtures"

def test_registry_canonicalization_and_deduplication(tmp_path):
    document = tmp_path / "sources.md"
    document.write_text("## NEWS\n- [One](https://Example.com/?utm_source=x&a=1)\n- [Same](https://example.com/?a=1#fragment)\n")
    rows, missing, parsed = parse_document(document)
    assert parsed == 2 and missing == 0 and len(rows) == 1
    assert canonical_url("https://Example.com/?utm_source=x&a=1#x") == "https://example.com/?a=1"

def test_rss_collects_entries_and_checkpoint(monkeypatch):
    body = (FIXTURES / "rss_valid.xml").read_bytes()
    response = SimpleNamespace(requested_url="https://example.com/rss.xml", final_url="https://example.com/rss.xml", status_code=200, content_type="application/rss+xml", body=body, redirect_chain=[], headers={"etag": "v1"})
    monkeypatch.setattr(rss, "fetch", lambda *args, **kwargs: response)
    result = rss.collect("https://example.com/rss.xml", ["example.com"])
    assert result["entries"][0]["entry_id"] == "item-1"
    assert result["checkpoint_after"]["etag"] == "v1"

def test_hash_and_ssrf_guards():
    assert sha256(b"trinetra") == "88c9e5de4ec786f2ab07469b8837fab851a9d73ea3977792d1e9d7ae188c4b24"
    for url in ("http://localhost", "http://127.0.0.1", "http://10.0.0.1", "http://[::1]", "file:///etc/passwd"):
        try: resolve_public(url)
        except ValueError: pass
        else: raise AssertionError(url)
