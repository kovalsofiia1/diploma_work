from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routers import auth
from app.routers import events
from app.routers import tickets
from app.routers import booking
from app.routers import checkin
from app.db.session import create_all_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For initial dev convenience; use Alembic migrations in real environments
    create_all_tables()
    yield


app = FastAPI(title="Event Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(events.router, tags=["events"])
app.include_router(tickets.router, tags=["tickets"])
app.include_router(booking.router, tags=["booking"])
app.include_router(checkin.router, tags=["checkin"])


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}

