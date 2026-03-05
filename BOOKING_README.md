🎟 Blockchain Ticket Booking & Check-in — Implementation Guide
🧱 Tech Stack

FastAPI

PostgreSQL

SQLAlchemy + Alembic

web3.py (blockchain integration)

Polygon Mumbai testnet

QR code generation

Blockchain is custodial: only backend wallet interacts with chain.

1. Project Structure
app/
 ├── api/
 │    ├── booking.py
 │    ├── tickets.py
 │    └── checkin.py
 ├── services/
 │    ├── booking_service.py
 │    ├── ticket_service.py
 │    └── blockchain_service.py
 ├── models/
 │    ├── user.py
 │    ├── event.py
 │    ├── seat.py
 │    ├── ticket.py
 │    └── checkin.py
 ├── core/
 │    ├── config.py
 │    └── security.py
 └── db/

2. Database Models
Ticket
id: UUID
user_id: UUID
event_id: UUID
seat_id: UUID
token_id: int
ticket_hash: str
used: bool
status: str  # minting | confirmed | failed
tx_hash: str
created_at: datetime
Checkin
id: UUID
ticket_id: UUID
scanned_at: datetime
staff_user_id: UUID

Add unique constraint on (event_id, seat_id).

3. Blockchain Service

Use:

web3.py

RPC from Alchemy or Infura

Contract deployed to Polygon Mumbai

Responsibilities
mint_ticket(token_id, event_id, seat_id, ticket_hash) -> tx_hash
get_ticket(token_id) -> {eventId, seatId, ticketHash, used}
mark_used(token_id) -> tx_hash

Load:

CONTRACT_ADDRESS

CONTRACT_ABI

PRIVATE_KEY

Sign and send transactions from backend wallet.

4. Ticket Hash

Generate deterministic hash:

ticket_hash = sha256(f"{ticket_id}{SECRET_KEY}")

Store in DB and on-chain.

5. Booking Flow
Endpoint
POST /book
Steps

Validate event & seat

Lock seat (DB transaction)

Create ticket with:

status = "minting"

used = false

Generate ticket_hash

Call blockchain_service.mint_ticket(...)

Save:

token_id

tx_hash

status = "confirmed"

Return QR payload:

{
  ticketId,
  ticketHash
}

Handle failure → set status = failed.

6. QR Code

QR must contain only:

ticketId
ticketHash

No personal data.

7. Check-in Flow
Endpoint
POST /checkin
body: { ticketId, ticketHash }
Steps

Find ticket in DB

Verify:

exists

not used

hash matches

status = confirmed

Fetch on-chain ticket:

compare ticketHash

ensure used == false

Mark used:

DB: used = true

create Checkin record

call blockchain_service.mark_used(token_id)

Return success

Second scan → reject.

8. Ticket API
GET /tickets/my
GET /tickets/{id}

Return QR payload only for owner.

9. Async Handling (MVP)

For simplicity:

wait for tx receipt during booking

Optional improvement:

FastAPI BackgroundTasks for minting

10. Security Rules

Private key in .env

Never expose token_id publicly without hash

Unique seat per event

Atomic check-in update

11. Smart Contract (minimal requirements)

Ticket struct:

eventId
seatId
ticketHash
used

Functions:

mintTicket(tokenId, eventId, seatId, ticketHash)
getTicket(tokenId)
markUsed(tokenId)

Only backend wallet can call mint/markUsed.


4. Development plan (best practice)
Phase 1 — No blockchain

mock blockchain service

build all APIs

test booking/check-in

Phase 2 — Local blockchain

deploy contract to Hardhat

connect FastAPI to local RPC

Phase 3 — Testnet

add Alchemy RPC

use real wallet key

deploy contract

real mint & check-in


Start with:

✅ fully local
✅ mock blockchain service
✅ real QR + DB logic

Then add:

➡ Hardhat local chain
➡ finally Polygon Mumbai

This gives you working system fast and avoids debugging blockchain while backend is unfinished.