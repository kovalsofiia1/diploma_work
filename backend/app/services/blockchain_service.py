from __future__ import annotations

import asyncio
from typing import Optional, Dict, Any
from uuid import uuid4

from app.core.config import get_settings

# Dynamic selection:
# - If ETHEREUM_RPC_URL and TICKET_CONTRACT_ADDRESS are set → use Hardhat/web3 service
# - Otherwise → fallback to in-memory mock (Phase 1)


def _use_hardhat() -> bool:
    s = get_settings()
    return bool(s.ethereum_rpc_url and s.ticket_contract_address)


if _use_hardhat():
    from app.blockchain.client import mint_ticket as _mint, mark_used as _mark
else:
    # Lightweight mock
    class _MockChain:
        def __init__(self) -> None:
            self._tickets: Dict[int, Dict[str, Any]] = {}

        def mint_ticket(self, token_id: int, event_id: int, seat_id: Optional[str], ticket_hash: str) -> str:
            if token_id in self._tickets:
                return self._make_tx("exist")
            self._tickets[token_id] = {"eventId": event_id, "seatId": seat_id, "ticketHash": ticket_hash, "used": False}
            return self._make_tx("mint")

        def mark_used(self, token_id: int) -> str:
            rec = self._tickets.get(token_id)
            if not rec:
                return self._make_tx("missing")
            rec["used"] = True
            return self._make_tx("used")

        @staticmethod
        def _make_tx(suffix: str) -> str:
            return "0x" + f"{suffix}-{uuid4().hex}".replace("-", "")[:64].ljust(64, "0")

    _mock = _MockChain()

    def _mint(token_id: int, event_id: int, seat_id: Optional[str], ticket_hash: str) -> str:
        return _mock.mint_ticket(token_id, event_id, seat_id, ticket_hash)

    def _mark(token_id: int) -> str:
        return _mock.mark_used(token_id)


def mint_ticket(token_id: int, event_id: int, seat_id: Optional[str], ticket_hash: str) -> str:
    return _mint(token_id, event_id, seat_id, ticket_hash)


async def mint_ticket_async(token_id: int, event_id: int, seat_id: Optional[str], ticket_hash: str) -> str:
    return await asyncio.to_thread(_mint, token_id, event_id, seat_id, ticket_hash)


def mark_used(token_id: int) -> str:
    return _mark(token_id)


async def mark_used_async(token_id: int) -> str:
    return await asyncio.to_thread(_mark, token_id)

