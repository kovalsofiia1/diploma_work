## Parser Service (FastAPI) — scrape external events by city

This is a small FastAPI microservice that **scrapes external events** from the code in `site-parsers/` and returns them to your main backend.

### What it does

- Accepts `cities: string[]`
- Scrapes **concurrently** (one task per city, with a concurrency limit)
- Returns **normalized event objects** (JSON) compatible with your backend `EventOut` shape
- Can **stream results in batches** (NDJSON) so the backend can ingest incrementally

### Run locally

From repo root:

```powershell
cd D:\code\python\diploma\parser-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

Health check: `GET /health`

### API

#### POST `/scrape/events`

Returns a single JSON payload with all results.

#### POST `/scrape/events/stream`

Returns **NDJSON** (`application/x-ndjson`) where each line is a JSON object containing a batch:

```json
{"batch_index":0,"items":[...],"done":false}
{"batch_index":1,"items":[...],"done":false}
{"batch_index":2,"items":[...],"done":true}
```


