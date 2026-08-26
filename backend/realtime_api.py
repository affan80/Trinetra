"""Small, consent-based realtime public-source research API.

Run with: uvicorn backend.realtime_api:app --reload --port 8000
The API searches public indexes only; it does not identify people from media.
"""
from __future__ import annotations

import asyncio
import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.verification_agent import verify_results

load_dotenv()

app = FastAPI(title="Trinetra Public Research API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","), allow_methods=["*"], allow_headers=["*"])
JOBS: dict[str, dict[str, Any]] = {}
UPLOAD_DIR = Path(os.getenv("TRINETRA_UPLOAD_DIR", "/tmp/trinetra_uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class ResearchRequest(BaseModel):
    target: str = Field(min_length=2, max_length=300)
    sources: list[str] = Field(default_factory=lambda: ["web", "news"])
    consent_confirmed: bool = Field(description="Analyst confirms they are authorized to research this target.")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_event(job: dict[str, Any], event: str, message: str, **data: Any) -> None:
    job["events"].append({"event": event, "message": message, "time": now(), **data})


def brave_search(query: str, kind: str) -> list[dict[str, Any]]:
    key = os.getenv("BRAVE_SEARCH_API_KEY", "")
    if not key:
        return []
    endpoint = f"https://api.search.brave.com/res/v1/{'news' if kind == 'news' else 'web'}/search"
    response = requests.get(endpoint, params={"q": query, "count": 10, "search_lang": "en"}, headers={"X-Subscription-Token": key, "Accept": "application/json"}, timeout=20)
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("news", {}).get("results", []) if kind == "news" else payload.get("web", {}).get("results", [])
    return [{"source": "Brave News" if kind == "news" else "Brave Web", "title": row.get("title", "Untitled"), "url": row.get("url", ""), "detail": row.get("description", ""), "date": row.get("age", "")} for row in rows if row.get("url")]


def gdelt_search(query: str) -> list[dict[str, Any]]:
    response = requests.get("https://api.gdeltproject.org/api/v2/doc/doc", params={"query": query, "mode": "artlist", "format": "json", "maxrecords": 10, "timespan": "1week"}, timeout=20)
    response.raise_for_status()
    return [{"source": "GDELT News", "title": row.get("title", "Untitled"), "url": row.get("url", ""), "detail": row.get("domain", ""), "date": row.get("seendate", "")} for row in response.json().get("articles", []) if row.get("url")]


async def run_job(job_id: str, request: ResearchRequest) -> None:
    job = JOBS[job_id]
    job["status"] = "running"
    add_event(job, "started", f"Researching public sources for {request.target}")
    try:
        results: list[dict[str, Any]] = []
        for source in request.sources:
            add_event(job, "source_started", f"Checking {source}", source=source)
            try:
                rows = await asyncio.to_thread(brave_search, request.target, source) if source in {"web", "news"} else await asyncio.to_thread(gdelt_search, request.target)
                results.extend(rows)
                add_event(job, "source_complete", f"{len(rows)} public results from {source}", source=source, count=len(rows))
            except Exception as exc:
                add_event(job, "source_error", f"{source} unavailable: {exc}", source=source)
        unique = {row["url"]: row for row in results if row.get("url")}
        job["results"] = list(unique.values())
        if os.getenv("OPENAI_API_KEY", "").strip():
            add_event(job, "verification_started", "AI agent is checking results against available evidence")
            try:
                assessment = await asyncio.to_thread(verify_results, request.target, job["results"])
                for item in assessment.get("items", []) if assessment else []:
                    index = item.get("id")
                    if isinstance(index, int) and 0 <= index < len(job["results"]):
                        job["results"][index]["verification"] = {
                            "status": item.get("status", "unresolved"),
                            "confidence": max(0.0, min(1.0, float(item.get("confidence", 0.0)))),
                            "reason": item.get("reason", "No reason provided."),
                            "sources": item.get("sources", []),
                        }
                job["verification"] = {"enabled": True, "summary": assessment.get("summary", "") if assessment else ""}
                add_event(job, "verification_complete", "AI evidence assessment complete")
            except Exception as exc:
                job["verification"] = {"enabled": True, "error": "AI verification unavailable"}
                add_event(job, "verification_error", f"AI verification unavailable: {exc}")
        else:
            job["verification"] = {"enabled": False, "message": "Set OPENAI_API_KEY to enable AI verification."}
            add_event(job, "verification_skipped", "AI verifier is not configured")
        job["status"] = "complete"
        add_event(job, "complete", f"Collected {len(job['results'])} public results")
    except Exception as exc:
        job["status"] = "failed"
        add_event(job, "failed", str(exc))


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "brave_configured": bool(os.getenv("BRAVE_SEARCH_API_KEY")), "ai_verifier_configured": bool(os.getenv("OPENAI_API_KEY")), "gdelt": "public"}


@app.post("/api/research", status_code=202)
async def create_research(request: ResearchRequest) -> dict[str, Any]:
    if not request.consent_confirmed:
        raise HTTPException(400, "Confirm that you are authorized to research this target.")
    job_id = uuid.uuid4().hex
    JOBS[job_id] = {"id": job_id, "target": request.target, "status": "queued", "created_at": now(), "results": [], "events": []}
    asyncio.create_task(run_job(job_id, request))
    return {"id": job_id, "status": "queued", "events_url": f"/api/research/{job_id}/events"}


@app.get("/api/research/{job_id}")
async def get_research(job_id: str) -> dict[str, Any]:
    if job_id not in JOBS:
        raise HTTPException(404, "Research job not found")
    return JOBS[job_id]


@app.get("/api/research/{job_id}/events")
async def research_events(job_id: str) -> StreamingResponse:
    if job_id not in JOBS:
        raise HTTPException(404, "Research job not found")
    async def stream():
        sent = 0
        while True:
            job = JOBS[job_id]
            for item in job["events"][sent:]:
                yield f"data: {json.dumps(item)}\n\n"
            sent = len(job["events"])
            if job["status"] in {"complete", "failed"} and sent == len(job["events"]):
                break
            await asyncio.sleep(0.5)
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/research/{job_id}/media", status_code=201)
async def upload_media(job_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    if job_id not in JOBS:
        raise HTTPException(404, "Research job not found")
    if file.content_type not in {"image/jpeg", "image/png", "image/webp", "video/mp4", "audio/mpeg", "audio/wav", "audio/ogg"}:
        raise HTTPException(415, "Only image, video, and audio files are supported")
    data = await file.read()
    if len(data) > 100 * 1024 * 1024:
        raise HTTPException(413, "Maximum file size is 100 MB")
    safe_name = f"{secrets.token_hex(8)}-{Path(file.filename or 'upload').name}"
    path = UPLOAD_DIR / safe_name
    path.write_bytes(data)
    return {"filename": file.filename, "stored_as": str(path), "bytes": len(data), "notice": "Stored as case context; never used for face identification."}
