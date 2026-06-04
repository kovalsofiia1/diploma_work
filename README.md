# Event Aggregation & Blockchain Ticketing System

A multi-service platform that aggregates events from external Ukrainian sources
(`karabas.com`, `concert.ua`, `dou.ua`), lets organizers publish their own events,
and issues tickets whose authenticity is anchored on a Polygon-compatible
blockchain.

The repository contains four cooperating components:

- `backend/` — FastAPI service: REST API, PostgreSQL persistence, business logic.
- `parser-service/` — FastAPI scraping micro-service, isolated from the main API.
- `frontend/` — Ionic + Angular SPA (also runs as a mobile app via Capacitor).
- `hardhat_chain/` — Hardhat project with the `TicketRegistry` smart contract.

---

## Quick Start (Run All Parts)

### 1) Backend API (`FastAPI`, port `8000`)

```powershell
cd D:\code\python\diploma\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

OR

```powershell
./start.ps1
```

Notes:
- Make sure PostgreSQL is running and `DATABASE_URL` in `backend/.env` points to your DB.
- Health check: `http://127.0.0.1:8000/health`.

### 2) Parser Service (`FastAPI`, port `8010`)

```powershell
cd D:\code\python\diploma\parser-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

OR

```powershell
./start.ps1
```

Notes:
- Backend uses `PARSER_SERVICE_URL` (default: `http://localhost:8010/scrape/events`).
- Health check: `http://127.0.0.1:8010/health`.

### 3) Hardhat Local Blockchain (optional, for real chain tx in dev)

```powershell
cd D:\code\python\diploma\hardhat_chain
.\start-hardhat.ps1
```

The script:
- starts a local Hardhat RPC at `127.0.0.1:8545`,
- deploys `TicketRegistry`,
- prints `TICKET_CONTRACT_ADDRESS` for backend `.env`.

If `ETHEREUM_RPC_URL` or `TICKET_CONTRACT_ADDRESS` are missing, the backend falls
back to an in-memory mock blockchain implementation, so the rest of the system
keeps working without a live chain.

### 4) Frontend (Ionic/Angular, port `8100`)

```powershell
cd D:\code\python\diploma\frontend
npm install
npm run dev
```

`proxy.conf.json` maps `/api` → `http://127.0.0.1:8000`, and `environment.ts`
already uses `apiBaseUrl: '/api'`.

---

## Frontend Start Modes

### Mode A: Local web / LAN (same Wi-Fi)

```powershell
cd D:\code\python\diploma\frontend
npm run dev
```

Open:
- PC: `http://localhost:8100`
- Phone (same Wi-Fi): `http://<YOUR_LAPTOP_IP>:8100`

### Mode B: Mobile web via ngrok

1. Start backend (`8000`) and frontend with proxy (`8100`).
2. In a new terminal:

```powershell
ngrok http 8100
```

3. Open the generated `https://...ngrok-free.app` URL on your phone.

The Angular dev server still applies the proxy config, so calls to `/api/*`
are forwarded to the local backend.

---

## Project Stack

Frontend:
- Ionic + Angular, Capacitor for native packaging
- NgRx for state management

Backend:
- FastAPI (Python)
- PostgreSQL + SQLAlchemy + Alembic

Scraping:
- Custom HTML/JSON parsers (httpx + BeautifulSoup)
- APScheduler for periodic jobs

Blockchain:
- Polygon / Ethereum-compatible chain (Hardhat for local dev)
- web3.py on the backend, Solidity for `TicketRegistry`

Auth:
- JWT (access + refresh)
- bcrypt for password hashing

Deployment:
- Docker + Docker Compose

---

# System Logic & Processes

The sections below describe how the system actually behaves at runtime, not just
what endpoints exist. They are the most important reference for understanding
the project.

## 1. Service Topology and Data Flow

```
Ionic SPA ──► Backend API ──► PostgreSQL
                  │
                  ├──► Parser Service ──► karabas.com / concert.ua / dou.ua
                  │
                  └──► Blockchain (Hardhat / Polygon) — TicketRegistry contract
```

Key principles:

- Scraping is fully isolated in `parser-service`. The backend only sees
  *normalized JSON events* via HTTP, never raw HTML.
- The backend is the only writer to PostgreSQL and the only client of the
  blockchain. The frontend never talks to the chain or the parser directly.
- The frontend uses streaming responses (NDJSON) for the city events feed,
  so users see cached results immediately and freshly scraped ones as they
  arrive.

## 2. Event Aggregation and Deduplication

External events come from three sources and are merged with internal
(organizer-created) events into a single `events` table distinguished by
`source_type` (`INTERNAL` / `EXTERNAL`).

### 2.1 Normalization in `parser-service`

Each source has its own adapter (`karabas_adapter.py`, `concert_adapter.py`,
`dou_adapter.py`). Adapters output a single shared schema `NormalizedEvent`
with fields like `name`, `startDate`, `endDate`, `location_name`, `city`,
`source`, `url`, `price_low/high`, `image`, `description`, `event_type`.

For `concert.ua`, server-rendered HTML is sometimes empty, so the scraper
falls back to the AJAX endpoint `concert.ua/ajax/load-more-city`. For both
`karabas` and `concert`, listing items can be optionally enriched in parallel
(`asyncio.Semaphore`) by fetching each event's detail page to obtain a
proper start/end date, full description and price.

Streaming mode (`/scrape/events/stream`) emits NDJSON batches as cities
finish, plus a final meta line, so the backend can ingest in chunks instead
of waiting for the whole job.

### 2.2 Deduplication in the backend

Inside `_upsert_scraped_items` (`backend/app/routers/events.py`) the backend
performs a two-stage deduplication:

1. **In-batch deduplication.** Items received from the parser are first
   uniqued in memory using `(source, url)` as the primary key, with
   `(source, name, startDate)` as fallback when `url` is missing. This kills
   duplicates that appear within a single scrape (e.g. an event listed on
   multiple city pages).
2. **Database deduplication.** Surviving URLs are normalized
   (`rstrip('/')`, trim) and looked up against `events.source_url`. Matches
   are *updated* (only fields that changed), non-matches are inserted.
   A secondary lookup by `(source_name, name, startDate)` catches items
   whose URL changed but whose identity is the same.

Each newly inserted external event gets a stable UID
(`f"external:{id}"`); internal events use `f"internal:{id}"`. The unified
events feed (`/events/all`) returns a `UnifiedEventOut` with a `kind` field
so the frontend can render both kinds uniformly.

### 2.3 Scrape coordination (per-city locking and TTL)

To keep scraping cheap and predictable, every city has a row in
`city_scrape_state` with `is_scraping` and `last_scraped_at` columns.

- When a user opens the events list for a city, the backend first returns
  existing DB content immediately (over NDJSON), then checks the state row.
- If the city was scraped less than `CITY_SCRAPE_TTL` (12h) ago, no new
  scrape is triggered.
- Otherwise the backend asks the parser-service for that city, runs the
  deduplication pipeline, marks the city scraped and streams the delta
  (new + updated events) to the client.
- `_claim_city_for_scraping` uses an atomic conditional `UPDATE` on
  `city_scrape_state` (only sets `is_scraping=True` if it was `False` and
  cooldown passed), which acts as a distributed lock and prevents two
  workers from scraping the same city in parallel.

### 2.4 Scheduled / popular-city scraping

`APScheduler` runs background jobs in `scheduler_service.py`:

- `schedule_city_scraping` — picks up to `MAX_CITIES_PER_RUN` (default 10)
  cities prioritized by recent user activity. The score is computed in SQL
  from `city_activity_log`:
  - subscription on a city → +10 points,
  - search/filter by city → +5 points,
  - over a 14-day rolling window.
  Cities from the `POPULAR_CITIES` env are added with score 1 as a fallback.
  Each chosen city is scraped behind the same lock as the on-demand path.
- `cleanup_past_external_events_job` — deletes EXTERNAL events whose
  `endDate` (or `startDate` if `endDate` is null) is in the past.
- `cleanup_city_activity_log_job` — purges `city_activity_log` rows older
  than the configured retention.
- `sync_cities_job` — pulls the canonical list of cities (with English
  spellings) from the parser-service so the backend can translate user
  selections into source-specific slugs.

### 2.5 Email digest for subscribed cities

`send_new_city_events_digest_job`:

- For every active user, gathers the cities they're subscribed to via
  `user_cities`.
- Looks up EXTERNAL events created after the user's
  `user_city_digest_state.last_sent_at` and matches their cities
  (case-insensitive).
- If matches exist, builds a single HTML+plain email summarising up to 20
  new events and sends it through Resend; updates `last_sent_at`.
- The combined `scrape_then_send_city_events_digest_job` chains scraping
  with the digest, so newly discovered events reach subscribers in the same
  cycle.

## 3. Tickets, QR Codes and Check-in

### 3.1 Booking pipeline

`book_ticket` creates a ticket with status `pending_onchain`, generates:

- `ticket_id` — random `uuid4().hex`,
- `code` — short human-readable identifier (`TKT-XXXXXXXXXX`),
- `ticket_hash = "0x" + sha256(ticket_id || TICKET_SECRET_KEY)` —
  collision-resistant fingerprint that doesn't leak any user data and is
  what gets anchored on-chain.

A QR token is issued separately. It is **not** the ticket id — it is a
short-lived JWT (`TICKET_QR_EXPIRES_MINUTES`) signed with the backend's
JWT secret, carrying `{ticket_id, event_id, exp}`. This means a screenshot
of the QR cannot be reused after expiry; the token is regenerated each time
the ticket is downloaded.

### 3.2 Async on-chain anchoring

After the row is committed, `mint_ticket_async` runs in a background task:

- Calls `TicketRegistry.mintTicket(token_id, event_id, seat_id, ticket_hash)`.
- On success: stores `tx_hash` and flips status to `confirmed_onchain`.
- On failure: status becomes `failed_onchain` so the rest of the system
  treats the ticket as invalid.

The chain client (`blockchain_service.py`) auto-selects between:

- **Real chain** via `web3.py` when `ETHEREUM_RPC_URL` and
  `TICKET_CONTRACT_ADDRESS` are configured;
- **In-memory mock** otherwise — it implements `mintTicket / markUsed /
  getTicket` with the same signatures so the rest of the codebase stays
  agnostic to the deployment mode.

### 3.3 PDF + email delivery

`send_ticket_pdf_email_async` builds a styled A4 PDF with ReportLab,
embeds the QR token rendered by `qrcode`, registers a Cyrillic-capable
font (Arial / DejaVu), and sends it as an email attachment via Resend.
Failures are swallowed so the booking flow itself never breaks because of
mail delivery problems.

### 3.4 Verification and check-in

`verify_ticket_qr` decodes the JWT QR token, then checks:

- ticket exists and matches the event,
- ticket isn't already used (`used == True` or `status == "used"`),
- on-chain confirmation hasn't failed (`status != "failed_onchain"`).

`checkin_ticket` reuses `verify_ticket_qr`, then atomically:

1. flips `used = True`, `status = "used"` and commits,
2. inserts a `Checkin` row referencing the staff user that scanned it,
3. enqueues `mark_ticket_used_async` — a background call to the chain's
   `markUsed(tokenId)` so the on-chain state reflects reality.

The double bookkeeping (DB + chain) lets the system stay responsive: the
gate accepts/rejects within a single DB round-trip, while the blockchain
record is updated asynchronously and is used as a public proof of the
ticket lifecycle.

## 4. Authentication, Roles and Authorization

- Passwords are hashed with bcrypt; JWT access + refresh pair is issued on
  login. Refresh rotates on use.
- User accounts have a `status` (`unverified`, `verified_user`, `admin`)
  driven by email verification and organizer applications.
- Per-event access is modelled by `event_users(event_id, user_id, role)`
  with two roles:
  - `organizer` — can edit the event and manage members,
  - `scanner` — can check tickets in but cannot edit the event.
  The creator of an internal event is implicitly an organizer and cannot
  be removed.
- Routes that mutate events use `_can_edit_event` (creator or organizer);
  scanner-tier access is checked with `_has_event_access`.
- Cancelling an event (`DELETE /events/{id}`) is non-destructive: the
  event is marked `CANCELLED`, all non-final tickets are flipped to
  `cancelled`, and each affected user receives a cancellation email.

## 5. Cities Reference Data

`cities` is a small reference table maintained both interactively
(`POST /cities/sync`) and on a schedule (`sync_cities_job`). It merges:

- live names from the parser's `/cities` endpoint (with `name_en` for
  source slugs),
- distinct cities used by INTERNAL events,
- a guaranteed `Online` entry.

The English-name column (`name_en`) is what the scheduler hands to the
parser-service so the right city URL is hit on each source (e.g. `kyiv`
vs `Київ`).

---

# Deployment

## Docker Compose

Required: Docker Engine 24.0+, Docker Compose 2.20+, Git.
Recommended server: 2 CPU, 4 GB RAM, 20 GB disk.

Services:

- `db` — PostgreSQL 15
- `backend` — FastAPI API on port 8000
- `parser-service` — FastAPI parser on port 8001
- `frontend` — Angular SPA served by Nginx on port 80

```bash
cp .env.example .env
# fill all secrets in .env
docker compose up --build -d
docker compose ps
```

Public endpoints after start:

- Frontend: `http://localhost`
- Backend Swagger UI: `http://localhost:8000/docs`
- Parser-service Swagger UI: `http://localhost:8001/docs`

Diagnostics:

```bash
docker compose logs -f
docker compose logs -f backend
docker compose logs -f parser-service
docker compose restart parser-service
```

---

# Documentation Deliverables

Technical documentation should cover:

- Architecture and service topology
- Database schema (entities + relationships)
- Authentication and role model
- Event aggregation, deduplication and scheduling logic
- Ticket lifecycle and blockchain anchoring
- Security mechanisms (JWT, QR JWT, hashing, bcrypt)

Diagrams:

- System architecture diagram
- ER diagram
- Use-case diagram
- Activity diagrams (booking, check-in, scrape cycle)
- Sequence diagrams (booking → mint, check-in → markUsed, city feed stream)
