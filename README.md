# Event Aggregation & Blockchain Ticketing System  
## Development Roadmap

---

## Quick Start (Run All Parts)

### 1) Backend API (`FastAPI`, port `8000`)

From project root:

```powershell
cd D:\code\python\diploma\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Notes:
- Make sure PostgreSQL is running and `DATABASE_URL` in `backend/.env` points to your DB.
- Health check: `http://127.0.0.1:8000/health`

### 2) Parser Service (`FastAPI`, port `8010`)

```powershell
cd D:\code\python\diploma\parser-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

Notes:
- Backend uses `PARSER_SERVICE_URL` (default: `http://localhost:8010/scrape/events`).
- Health check: `http://127.0.0.1:8010/health`

### 3) Hardhat Local Blockchain (optional, for real chain tx in dev)

```powershell
cd D:\code\python\diploma\hardhat_chain
.\start-hardhat.ps1
```

Or:

```powershell
cd D:\code\python\diploma\hardhat_chain
.\start-hardhat.cmd
```

The script:
- starts local Hardhat RPC (`127.0.0.1:8545`),
- deploys `TicketRegistry`,
- prints `TICKET_CONTRACT_ADDRESS` for backend `.env`.

If blockchain env vars are missing, backend falls back to mock blockchain mode.

### 4) Frontend (Ionic/Angular, port `8100`)

```powershell
cd D:\code\python\diploma\frontend
npm install
npm run dev
```

`proxy.conf.json` maps `/api` -> `http://127.0.0.1:8000`, and `environment.ts` already uses:
- `apiBaseUrl: '/api'`

---

## Frontend Start Modes

### Mode A: Local web/LAN (same Wi-Fi)

Use:

```powershell
cd D:\code\python\diploma\frontend
npm run dev
```

Open:
- PC: `http://localhost:8100`
- Phone (same Wi-Fi): `http://<YOUR_LAPTOP_IP>:8100`

### Mode B: Mobile web via ngrok (works even if LAN access is blocked)

1. Start backend (`8000`) and frontend with proxy (`8100`) as above.
2. In a new terminal run:

```powershell
ngrok http 8100
```

3. Open the generated `https://...ngrok-free.app` URL on your phone.

Because frontend still runs with proxy config, calls to `/api/*` are forwarded by Angular dev server to local backend on `127.0.0.1:8000`.

---

## PROJECT STACK

Frontend:
- Ionic + Angular
- Capacitor

Backend:
- FastAPI (Python)
- PostgreSQL
- SQLAlchemy + Alembic

Scraping:
- Scrapy / Requests
- APScheduler / Cron

Blockchain:
- Polygon testnet (or Ethereum testnet)
- web3.py / ethers.js

Auth:
- JWT (Access + Refresh)

Deployment:
- Docker + Docker Compose

---

# PHASE 0 — SYSTEM DESIGN (PLANNING)

## 0.1 Define MVP Functional Requirements

### User:
- Registration / Login
- View events
- Search and filters
- Event details
- Ticket booking
- View booked tickets
- QR code display

### Organizer:
- Create event
- Edit event
- Manage bookings

### System:
- External events aggregation
- Blockchain ticket verification

---

## 0.2 Database Entities (ER Model)

Main tables:

- User
- Event (Internal)
- ExternalEvent
- Booking
- Ticket
- BlockchainRecord

---

## 0.3 System Architecture

High-level architecture:

Ionic App (Web + Mobile)
↓
FastAPI Backend
↓
PostgreSQL Database
↓
Blockchain Network

Scraper Service
↓
Backend API


---

# PHASE 1 — BACKEND SKELETON (FastAPI)

## 1.1 Project Initialization

Tasks:
- Create virtual environment
- Install dependencies
- Create FastAPI project structure
- Setup main.py

---

## 1.2 Database Setup

Tasks:
- Connect PostgreSQL
- Configure SQLAlchemy
- Setup Alembic migrations
- Create base models

---

## 1.3 Authentication Module

Features:
- User registration
- User login
- Password hashing (bcrypt)
- JWT token generation
- Refresh token support

---

## 1.4 Role Management

User roles:

- USER
- ORGANIZER
- ADMIN

Purpose:
- Restrict event creation
- Manage admin features

---

# PHASE 2 — EVENTS MANAGEMENT

## 2.1 Internal Events (Platform Created)

API Endpoints:

POST /events
GET /events
GET /events/{id}
PUT /events/{id}
DELETE /events/{id}


Features:
- CRUD operations
- Event ownership
- Validation

---

## 2.2 External Events Module

Tasks:
- Create external_events table
- Store aggregated events
- Save source information

---

## 2.3 Unified Events API

Endpoint:

GET /events/all


Purpose:
- Combine internal and external events
- Return unified response for frontend

---

# PHASE 3 — SCRAPING & WORKERS

## 3.1 Scraper Project Structure

scraper/
├── sources/
│ ├── eventbrite.py
│ ├── meetup.py
│ └── local_events.py
├── normalizer.py
├── deduplicator.py
├── sender.py
└── scheduler.py


---

## 3.2 Data Normalization

Normalize scraped data into unified format:

- title
- start_date
- location
- url
- source

---

## 3.3 Deduplication Logic

Generate unique hash:

SHA256(title + date + location + source)


Database:

- UNIQUE constraint on external_hash

---

## 3.4 Scheduler Setup

Options:
- APScheduler (Python)
- Linux Cron

Execution:

- Once per day
- Automatic scraping start

---

## 3.5 Import API Endpoint

Backend endpoint:

POST /external-events/import


Purpose:
- Receive scraped data
- Validate
- Save unique records

---

# PHASE 4 — BOOKING & TICKETS

## 4.1 Booking Flow

Endpoint:

POST /events/{id}/book


Backend logic:

- Check available seats
- Create booking record
- Generate ticket

---

## 4.2 Ticket Model

Fields:

- id
- event_id
- user_id
- qr_code
- status
- created_at

---

## 4.3 QR Code Generation

Tasks:

- Generate QR code image
- Encode ticketId
- Store base64 or file path

---

# PHASE 5 — BLOCKCHAIN INTEGRATION

## 5.1 Smart Contract

Functions:

registerTicket(ticketHash)
verifyTicket(ticketId)


Purpose:

- Store immutable ticket proof
- Enable decentralized verification

---

## 5.2 Backend Blockchain Service

Responsibilities:

- Generate ticket hash
- Send transaction
- Save transaction hash
- Read verification status

---

## 5.3 Ticket Verification Flow

Process:

Scan QR code
→ Extract ticketId
→ Backend query
→ Blockchain verification
→ Validation result


---

# PHASE 6 — FRONTEND (IONIC)

## 6.1 Authentication UI

Screens:

- Login
- Registration
- Token storage
- Logout

---

## 6.2 Events UI

Features:

- Events list
- Filters
- Search
- Event details page

---

## 6.3 Booking UI

Flow:

- Book button
- Confirmation screen
- QR code display

---

## 6.4 Ticket Scanner UI

Features:

- Camera access
- QR scanning
- Verification status display

---

# PHASE 7 — DEPLOYMENT

## 7.1 Docker Compose Setup

Before deployment, install Docker Engine 24.0+, Docker Compose 2.20+ and Git.
Recommended minimum server resources: 2 CPU cores, 4 GB RAM and 20 GB disk space.

Services:

- `db` — PostgreSQL 15
- `backend` — FastAPI API on port 8000
- `parser-service` — FastAPI event parser on port 8001
- `frontend` — Angular SPA served by Nginx on port 80

Create the environment file from the template:

```bash
cp .env.example .env
```

Fill all secret values in `.env`, then build and start the stack:

```bash
docker compose up --build -d
```

Check container status:

```bash
docker compose ps
```

The application is available at:

- Frontend: http://localhost
- Backend Swagger UI: http://localhost:8000/docs
- Parser-service Swagger UI: http://localhost:8001/docs

Useful diagnostics commands:

```bash
docker compose logs -f
docker compose logs -f backend
docker compose logs -f parser-service
docker compose restart parser-service
```

---

## 7.2 Demo Data Preparation

Tasks:

- Create seed scripts
- Add demo events
- Create test users

---

# PHASE 8 — DOCUMENTATION

## Technical Documentation

Include:

- Architecture description
- Database schema
- API specification
- Security mechanisms
- Blockchain integration description

---

## Diagrams

Prepare:

- System architecture diagram
- ER diagram
- Use-case diagram
- Activity diagrams
- Sequence diagrams

---

# DEVELOPMENT STRATEGY

## Recommended Order

1. Backend + Authentication
2. Events module
3. Booking logic
4. Scraper integration
5. Blockchain integration
6. Frontend UI
7. Deployment and testing

---

## Time Planning (Example)

Week 1:
- Backend base
- Auth
- Events

Week 2:
- Scraper
- Booking

Week 3:
- Blockchain
- QR verification

Week 4:
- Ionic UI

Week 5:
- Testing
- Documentation
- Demo preparation

---

# IMPORTANT NOTES

- Start with core functionality first
- Add blockchain and scraping later
- Focus on stable MVP
- Avoid overengineering
- Keep architecture modular

---

