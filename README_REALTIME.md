# Realtime public-source API

This service runs bounded searches against public indexes. It does not bypass logins, scrape private accounts, access another person's computer, or identify a person from a face, voice, image, video, or audio file.

## Configure the search key

Copy `.env.example` to `.env` in the repository root and set `BRAVE_SEARCH_API_KEY` to the key from your Brave Search API account. Keep `.env` private; do not paste keys into the frontend or commit them. GDELT news search works without a key.

## Run

```bash
python -m pip install -r requirements.txt
uvicorn backend.realtime_api:app --reload --port 8000
```

Create a job:

```bash
curl -X POST http://localhost:8000/api/research \
  -H 'content-type: application/json' \
  -d '{"target":"Example Organization","sources":["web","news"],"consent_confirmed":true}'
```

Subscribe to `GET /api/research/{id}/events` with an EventSource client for live progress, or poll `GET /api/research/{id}`. Upload case context to `/api/research/{id}/media` as multipart field `file`.

## Optional AI verification agent

Set these server-side variables in `.env` to assess each public result against
its available evidence:

```bash
OPENAI_API_KEY=your_key_here
OPENAI_VERIFIER_MODEL=gpt-5
```

The key is read only by the backend. Do not put it in `frontend/.env` or any
`NEXT_PUBLIC_*` variable. Without a key, research still runs and results are
explicitly marked as not AI-verified. With the agent enabled, each result can
include `verification.status`, `verification.confidence`,
`verification.reason`, and source URLs.
