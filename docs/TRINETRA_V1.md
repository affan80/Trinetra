# Trinetra V1 — Multimodal OSINT Investigation Engine

This repository contains a deliberately bounded investigation workflow in
`services/investigations/`. It establishes the V1 trust boundary:

```text
Investigation -> validated plan -> collectors -> raw artifact + hash
              -> normalized evidence -> entities / claims -> verification -> report
```

`CollectionPlan` and every collector result are Pydantic models. Planner output
therefore cannot select arbitrary infrastructure, execute code, or bypass the
collector registry. `InvestigationRepository` is a local development adapter;
it preserves raw bytes under `data/raw/investigations/<INV>/` and exposes the
same interface a future PostgreSQL/MinIO implementation will satisfy.

## Plug-and-play Docker run

The lightweight V1 stack is independent of the legacy Kafka/Spark compose file:

    docker compose -f docker-compose.v1.yml up --build

The API is available at http://localhost:8000 and raw uploads are retained in
the named Docker volume trinetra_raw.

## Local run

Install the lightweight dependencies in a Python 3.11 environment, then start
the API:

    pip install -r requirements-v1.txt
    uvicorn services.api.app:app --reload

Start the analyst workstation in a second terminal:

```bash
python -m tui.app.main
```

Select an intake mode and provide an image, video, audio, PDF, document, URL,
public social URL, or text. Trinetra preserves the original, calculates a
SHA-256 hash, extracts safe local metadata, records observable identifiers, and
creates evidence-search hypotheses. The API never bypasses login, CAPTCHA,
private profiles, access controls, or platform restrictions.

Image metadata and perceptual hashes are available immediately. Direct PDF text
is extracted locally; OCR, ASR, keyframes, object/logo/landmark recognition and
permitted-source adapters are explicit pluggable capabilities. When unavailable,
the dossier says so rather than inventing an observation.

## API flow

1. POST /v1/intake/upload accepts a local file.
2. POST /v1/intake/text and POST /v1/intake/url accept analyst-supplied text or public URLs.
3. GET /v1/investigations/{id}/media returns media intelligence and provenance.
4. GET /v1/investigations/{id}/dossier returns observed identifiers, hypotheses, artifacts, evidence, and claims.
5. The existing run route executes bounded collection, analysis, verification, and reporting when permitted collectors are configured.

The verifier currently records *model-assessed confidence*, not calibrated
probability. A claim is only marked supported when it has an explicit stored
evidence link; V1 does not claim independent corroboration from a single source.
