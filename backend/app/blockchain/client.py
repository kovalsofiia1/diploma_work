from __future__ import annotations

import json
import os
from typing import Any, Optional

from web3 import Web3
from web3.contract import Contract

from app.core.config import get_settings

_w3: Optional[Web3] = None
_contract: Optional[Contract] = None


def _load_abi(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _init() -> tuple[Web3, Contract]:
    global _w3, _contract
    if _w3 is not None and _contract is not None:
        return _w3, _contract

    settings = get_settings()
    if not settings.ethereum_rpc_url:
        raise RuntimeError("ETHEREUM_RPC_URL is not set")
    if not settings.ticket_contract_address:
        raise RuntimeError("TICKET_CONTRACT_ADDRESS is not set")

    w3 = Web3(Web3.HTTPProvider(settings.ethereum_rpc_url))
    if not w3.is_connected():
        raise RuntimeError(f"Cannot connect to RPC at {settings.ethereum_rpc_url}")

    address = Web3.to_checksum_address(settings.ticket_contract_address)
    abi_path = settings.ticket_contract_abi_path
    if abi_path and os.path.exists(abi_path):
        abi = _load_abi(abi_path)
    else:
        here = os.path.dirname(__file__)
        abi = _load_abi(os.path.join(here, "..", "core", "abi", "booking_ticket.json"))
    contract = w3.eth.contract(address=address, abi=abi)

    _w3, _contract = w3, contract
    return w3, contract


def _get_sender(w3: Web3) -> str:
    settings = get_settings()
    if settings.ethereum_private_key:
        account = w3.eth.account.from_key(settings.ethereum_private_key)
        return account.address

    accounts = w3.eth.accounts
    if not accounts:
        raise RuntimeError("No unlocked accounts available")
    return accounts[0]


def _send_tx(func, w3: Web3) -> str:
    settings = get_settings()
    sender = _get_sender(w3)

    if settings.ethereum_private_key:
        built = func.build_transaction(
            {
                "from": sender,
                "nonce": w3.eth.get_transaction_count(sender),
                "gas": 800_000,
            }
        )
        signed = w3.eth.account.sign_transaction(built, private_key=settings.ethereum_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    else:
        tx_hash = func.transact({"from": sender, "gas": 800_000})

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt.transactionHash.hex()


def mint_ticket(token_id: int, event_id: int, seat_id: Optional[str], ticket_hash: str) -> str:
    w3, contract = _init()
    func = contract.functions.mintTicket(int(token_id), int(event_id), seat_id or "", ticket_hash)
    return _send_tx(func, w3)


def mark_used(token_id: int) -> str:
    w3, contract = _init()
    func = contract.functions.markUsed(int(token_id))
    return _send_tx(func, w3)
