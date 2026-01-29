# Event Aggregation & Blockchain Ticketing System  
## Development Roadmap

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

Services:

- backend
- postgres
- scraper

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

