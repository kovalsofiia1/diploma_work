from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

from web3 import Web3
from web3.contract import Contract
from web3.types import TxParams

from app.core.config import get_settings


_w3: Optional[Web3] = None
_contract: Optional[Contract] = None


def _load_abi(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def init_blockchain() -> tuple[Web3, Contract]:
    global _w3, _contract
    if _w3 is not None and _contract is not None:
        return _w3, _contract

    settings = get_settings()
    rpc = settings.ethereum_rpc_url
    if not rpc:
        raise RuntimeError("ETHEREUM_RPC_URL is not configured")
    w3 = Web3(Web3.HTTPProvider(rpc))
    if not w3.is_connected():
        raise RuntimeError(f"Failed to connect to Ethereum RPC at {rpc}")

    address = Web3.to_checksum_address(settings.ticket_contract_address) if settings.ticket_contract_address else None
    if not address:
        raise RuntimeError("TICKET_CONTRACT_ADDRESS is not configured")

    abi_path = settings.ticket_contract_abi_path
    if abi_path and os.path.exists(abi_path):
        abi = _load_abi(abi_path)
    else:
        # Fallback to bundled minimal ABI
        here = os.path.dirname(__file__)
        abi = _load_abi(os.path.join(here, "abi", "ticket.json"))

    contract = w3.eth.contract(address=address, abi=abi)
    _w3, _contract = w3, contract
    return w3, contract


def _get_default_from_address(w3: Web3) -> str:
    # Prefer private key if set; otherwise use first unlocked account (Hardhat provides unlocked accounts)
    settings = get_settings()
    if settings.ethereum_private_key:
        acct = w3.eth.account.from_key(settings.ethereum_private_key)
        return acct.address
    accounts = w3.eth.accounts
    if not accounts:
        raise RuntimeError("No accounts available for sending transactions")
    return accounts[0]


def store_ticket_hash(hash_hex: str) -> str:
    """
    Calls storeTicket(bytes32) on the smart contract.
    Returns blockchain transaction hash (0x...).
    Ensures idempotency by tolerating 'already stored' reverts (best-effort).
    """
    w3, contract = init_blockchain()
    from_addr = _get_default_from_address(w3)

    # Prepare tx
    tx: TxParams = {
        "from": from_addr,
        "nonce": w3.eth.get_transaction_count(from_addr),
        "gas": 500_000,
    }

    settings = get_settings()
    try:
        if settings.ethereum_private_key:
            # Sign locally
            built = contract.functions.storeTicket(hash_hex).build_transaction(
                {
                    "from": from_addr,
                    "nonce": tx["nonce"],
                    "gas": tx["gas"],
                }
            )
            signed = w3.eth.account.sign_transaction(built, private_key=settings.ethereum_private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        else:
            # Use unlocked account on Hardhat
            tx_hash = contract.functions.storeTicket(hash_hex).transact(tx)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.transactionHash.hex()
    except Exception:
        # Best-effort idempotency: if it failed, check verifyTicket; if already stored, fake a tx hash '0x0...exist'
        try:
            if verify_ticket_hash(hash_hex):
                # Indicate existence without a concrete tx hash; callers may keep None instead
                return "0x" + "exist".encode().hex().ljust(64, "0")
        except Exception:
            pass
        raise


def verify_ticket_hash(hash_hex: str) -> bool:
    """
    Calls verifyTicket(bytes32) on the smart contract.
    """
    _, contract = init_blockchain()
    return bool(contract.functions.verifyTicket(hash_hex).call())


