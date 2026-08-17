from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from services.shared.redis_client import ping_redis, get_redis_client
from services.shared.redis_metrics import RedisMetrics
from services.shared.redis_queue import RedisQueue
from services.shared.url_frontier import UrlFrontier
from services.investigations import InvestigationRepository, InvestigationWorkflow
from services.investigations.multimodal import MultimodalIngestor
from services.investigations.schemas import (
    Investigation, InvestigationCreate, InvestigationStatus, TextInputRequest, UrlInputRequest,
)

app = FastAPI(title="Trinetra V1 OSINT API", version="0.1.0")
metrics = RedisMetrics()
raw_items_queue = RedisQueue("raw_items")
investigation_repository = InvestigationRepository()
investigation_workflow = InvestigationWorkflow(investigation_repository)
multimodal_ingestor = MultimodalIngestor(investigation_repository)

@app.get("/")
async def root():
    return {
        "status": "online",
        "redis_connected": ping_redis(),
        "message": "Welcome to Trinetra V1 OSINT API",
    }

@app.get("/health")
async def health_check():
    if not ping_redis():
        raise HTTPException(status_code=503, detail="Redis connection failed")
    return {"status": "healthy", "redis": "connected"}

@app.get("/stats")
async def get_stats():
    frontier = UrlFrontier(metrics=metrics)
    return {
        "metrics": metrics.get_all_metrics(),
        "queue_length": raw_items_queue.length(),
        "frontier": frontier.stats(),
    }

@app.get("/frontier/stats")
async def get_frontier_stats():
    frontier = UrlFrontier(metrics=metrics)
    return frontier.stats()

@app.get("/frontier/dead-letters")
async def get_frontier_dead_letters(limit: int = 20):
    frontier = UrlFrontier(metrics=metrics)
    return {
        "dead_letter_length": frontier.dead_letter_length(),
        "items": frontier.get_dead_letters(limit=limit),
    }

@app.post("/items/test")
async def push_test_item(title: str, url: str):
    item = {
        "title": title,
        "url": url,
        "source": "api_test"
    }
    raw_items_queue.push(item)
    metrics.increment("api_test_items")
    return {"message": "Item pushed to queue", "item": item}


def get_investigation_or_404(investigation_id: str) -> Investigation:
    investigation = investigation_repository.investigations.get(investigation_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation


@app.post("/v1/investigations", response_model=Investigation, status_code=201)
async def create_investigation(payload: InvestigationCreate):
    investigation = Investigation(
        id=investigation_repository.next_id("INV", investigation_repository.investigations),
        **payload.model_dump(),
    )
    investigation_repository.investigations[investigation.id] = investigation
    investigation_repository.log(investigation.id, "System", "Investigation created")
    return investigation


@app.get("/v1/investigations", response_model=list[Investigation])
async def list_investigations():
    return list(investigation_repository.investigations.values())


@app.post("/v1/investigations/{investigation_id}/run")
async def run_investigation(investigation_id: str):
    investigation = get_investigation_or_404(investigation_id)
    if investigation.status == InvestigationStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Investigation is already running")
    report = investigation_workflow.run(investigation)
    return {"investigation": investigation, "report": report}


@app.get("/v1/investigations/{investigation_id}/dashboard")
async def investigation_dashboard(investigation_id: str):
    investigation = get_investigation_or_404(investigation_id)
    evidence = investigation_repository.evidence[investigation_id]
    source_counts = {source.value: 0 for source in investigation.source_types}
    for row in evidence:
        source = row.provenance.source_type.value
        if source in source_counts:
            source_counts[source] += 1
    claims = investigation_repository.claims[investigation_id]
    status_counts = {"supported": 0, "contradicted": 0, "unresolved": 0, "insufficient": 0}
    for claim in claims:
        status_counts[claim.status] = status_counts.get(claim.status, 0) + 1
    return {
        "investigation": investigation,
        "collection": source_counts,
        "intelligence": {
            "entities": len(investigation_repository.entities[investigation_id]),
            "claims": len(claims),
            "events": 0,
            "locations": 0,
        },
        "evidence": {"total": len(evidence), **status_counts},
        "agent_activity": investigation_repository.activities[investigation_id],
    }


@app.get("/v1/investigations/{investigation_id}/evidence")
async def list_evidence(investigation_id: str):
    get_investigation_or_404(investigation_id)
    return investigation_repository.evidence[investigation_id]


@app.get("/v1/investigations/{investigation_id}/entities")
async def list_entities(investigation_id: str):
    get_investigation_or_404(investigation_id)
    return investigation_repository.entities[investigation_id]


@app.get("/v1/investigations/{investigation_id}/claims")
async def list_claims(investigation_id: str):
    get_investigation_or_404(investigation_id)
    return investigation_repository.claims[investigation_id]


@app.get("/v1/investigations/{investigation_id}/report")
async def get_report(investigation_id: str):
    get_investigation_or_404(investigation_id)
    report = investigation_repository.reports.get(investigation_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report has not been generated")
    return report


def create_input_investigation(title: str, target: str, objective: str) -> Investigation:
    investigation = Investigation(
        id=investigation_repository.next_id("INV", investigation_repository.investigations),
        title=title, target=target, objective=objective,
    )
    investigation_repository.investigations[investigation.id] = investigation
    investigation_repository.log(investigation.id, "System", "Multimodal investigation created")
    investigation.status = InvestigationStatus.RUNNING
    investigation_workflow.plan(investigation)
    investigation_repository.log(investigation.id, "Search Planner", "Search hypotheses await configured permitted-source collectors")
    return investigation


@app.post("/v1/intake/text", status_code=201)
async def intake_text(payload: TextInputRequest):
    investigation = create_input_investigation(payload.title, payload.target, payload.objective)
    artifact = multimodal_ingestor.ingest_text(investigation, payload.text)
    return {"investigation": investigation, "artifact": artifact}


@app.post("/v1/intake/url", status_code=201)
async def intake_url(payload: UrlInputRequest):
    investigation = create_input_investigation(payload.title, payload.target, payload.objective)
    try:
        artifact = multimodal_ingestor.ingest_url(investigation, payload.url)
    except ValueError as exc:
        del investigation_repository.investigations[investigation.id]
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"investigation": investigation, "artifact": artifact}


@app.post("/v1/intake/upload", status_code=201)
async def intake_upload(
    file: UploadFile = File(...),
    title: str = Form(default="Multimodal OSINT investigation"),
    target: str = Form(default="Analyst-provided media"),
    objective: str = Form(default="Extract observable information and identify evidence gaps."),
):
    if not file.filename:
        raise HTTPException(status_code=422, detail="A filename is required")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded file is empty")
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="V1 upload limit is 100 MB")
    investigation = create_input_investigation(title, target, objective)
    artifact = multimodal_ingestor.ingest_file(investigation, file.filename, file.content_type, content)
    return {"investigation": investigation, "artifact": artifact}


@app.get("/v1/investigations/{investigation_id}/media")
async def list_media(investigation_id: str):
    get_investigation_or_404(investigation_id)
    return investigation_repository.artifacts[investigation_id]


@app.get("/v1/investigations/{investigation_id}/media/{artifact_id}/original")
async def get_original_media(investigation_id: str, artifact_id: str):
    get_investigation_or_404(investigation_id)
    artifact = next((row for row in investigation_repository.artifacts[investigation_id] if row.artifact_id == artifact_id), None)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Media artifact not found")
    path = Path(artifact.original_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Original artifact is unavailable")
    return FileResponse(path, media_type=artifact.mime_type, filename=artifact.filename)


@app.get("/v1/investigations/{investigation_id}/dossier")
async def dossier(investigation_id: str):
    investigation = get_investigation_or_404(investigation_id)
    artifacts = investigation_repository.artifacts[investigation_id]
    mentions = list(dict.fromkeys(value for artifact in artifacts for value in artifact.entities))
    return {
        "investigation": investigation,
        "observed_identifiers": mentions,
        "search_hypotheses": list(dict.fromkeys(value for artifact in artifacts for value in artifact.search_hypotheses)),
        "artifacts": artifacts,
        "evidence": investigation_repository.evidence[investigation_id],
        "claims": investigation_repository.claims[investigation_id],
        "notice": "Observed identifiers and model outputs are leads, not identity or location determinations.",
    }


@app.get("/v1/investigations/{investigation_id}/dossier/entities/{entity_name}")
async def entity_dossier(investigation_id: str, entity_name: str):
    get_investigation_or_404(investigation_id)
    artifacts = investigation_repository.artifacts[investigation_id]
    matched = [
        artifact for artifact in artifacts
        if any(entity.casefold() == entity_name.casefold() for entity in artifact.entities)
    ]
    if not matched:
        raise HTTPException(status_code=404, detail="Observed entity not found")
    return {
        "name": entity_name,
        "classification": "observed_identifier",
        "artifacts": matched,
        "notice": "This is an observed identifier, not a resolved person, organization, or location.",
    }
