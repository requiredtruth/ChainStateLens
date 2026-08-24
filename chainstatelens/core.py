"""Strict parsing and deterministic state projection."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
HASH32 = re.compile(r"^0x[0-9a-fA-F]{64}$")
HEX = re.compile(r"^0x[0-9a-fA-F]*$")


class LensError(ValueError):
    """Input is incomplete, inconsistent, or unsafe."""


def quantity(value: Any, label: str) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)", value):
        raise LensError(f"{label} must be a canonical JSON-RPC hex quantity")
    return int(value, 16)


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class Target:
    label: str
    address: str
    storage_slots: tuple[str, ...]


@dataclass(frozen=True)
class Spec:
    blocks: tuple[int, ...]
    targets: tuple[Target, ...]


def parse_spec(raw: Any) -> Spec:
    if not isinstance(raw, dict) or set(raw) != {"blocks", "targets"}:
        raise LensError("spec must contain only blocks and targets")
    blocks = raw["blocks"]
    if not isinstance(blocks, list) or not blocks or any(type(x) is not int or x < 0 for x in blocks):
        raise LensError("blocks must be a non-empty list of non-negative integers")
    if blocks != sorted(set(blocks)):
        raise LensError("blocks must be unique and increasing")
    targets_raw = raw["targets"]
    if not isinstance(targets_raw, list) or not targets_raw:
        raise LensError("targets must be a non-empty list")
    targets: list[Target] = []
    labels: set[str] = set()
    for item in targets_raw:
        if not isinstance(item, dict) or set(item) != {"label", "address", "storage_slots"}:
            raise LensError("each target requires label, address, and storage_slots")
        label, address, slots = item["label"], item["address"], item["storage_slots"]
        if not isinstance(label, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", label):
            raise LensError("target label must be a short lowercase identifier")
        if label in labels:
            raise LensError(f"duplicate target label: {label}")
        if not isinstance(address, str) or not ADDRESS.fullmatch(address):
            raise LensError(f"invalid address for {label}")
        if not isinstance(slots, list) or len(slots) > 32:
            raise LensError(f"storage_slots for {label} must be a list of at most 32 entries")
        if any(not isinstance(s, str) or not HASH32.fullmatch(s) for s in slots):
            raise LensError(f"storage slot for {label} must be 32-byte hex")
        if len(set(s.lower() for s in slots)) != len(slots):
            raise LensError(f"duplicate storage slot for {label}")
        labels.add(label)
        targets.append(Target(label, address.lower(), tuple(s.lower() for s in slots)))
    return Spec(tuple(blocks), tuple(targets))


def project(spec: Spec, evidence: Any) -> dict[str, Any]:
    """Validate captured RPC evidence and produce a deterministic feature matrix."""
    if not isinstance(evidence, dict) or set(evidence) != {"chain_id", "captures"}:
        raise LensError("evidence must contain only chain_id and captures")
    chain_id = quantity(evidence["chain_id"], "chain_id")
    captures = evidence["captures"]
    if not isinstance(captures, list) or len(captures) != len(spec.blocks):
        raise LensError("capture count must equal requested block count")
    rows: list[dict[str, Any]] = []
    previous_timestamp = -1
    for expected, capture in zip(spec.blocks, captures):
        rows.extend(_project_capture(spec, capture, expected, previous_timestamp))
        previous_timestamp = quantity(capture["block"]["timestamp"], "block.timestamp")
    report = {"schema": "chainstatelens/report-1", "chain_id": chain_id, "rows": rows}
    report["report_sha256"] = canonical_hash(report)
    return report


def _project_capture(spec: Spec, capture: Any, expected: int, previous_timestamp: int) -> list[dict[str, Any]]:
    if not isinstance(capture, dict) or set(capture) != {"block", "confirm_hash", "accounts"}:
        raise LensError("capture must contain block, confirm_hash, and accounts")
    block = capture["block"]
    needed = {"number", "hash", "timestamp", "gasUsed", "gasLimit", "baseFeePerGas", "transactions"}
    if not isinstance(block, dict) or set(block) != needed:
        raise LensError("block fields are incomplete or unexpected")
    number = quantity(block["number"], "block.number")
    if number != expected:
        raise LensError(f"expected block {expected}, got {number}")
    block_hash = block["hash"]
    if not isinstance(block_hash, str) or not HASH32.fullmatch(block_hash):
        raise LensError("block.hash must be 32-byte hex")
    if capture["confirm_hash"] != block_hash:
        raise LensError(f"block {number} changed during capture")
    timestamp = quantity(block["timestamp"], "block.timestamp")
    if timestamp <= previous_timestamp:
        raise LensError("block timestamps must increase")
    gas_used = quantity(block["gasUsed"], "block.gasUsed")
    gas_limit = quantity(block["gasLimit"], "block.gasLimit")
    if gas_limit == 0 or gas_used > gas_limit:
        raise LensError("invalid block gas usage")
    base_fee = None if block["baseFeePerGas"] is None else quantity(block["baseFeePerGas"], "block.baseFeePerGas")
    txs = block["transactions"]
    if not isinstance(txs, list) or any(not isinstance(x, str) or not HASH32.fullmatch(x) for x in txs):
        raise LensError("transactions must be hashes")
    accounts = capture["accounts"]
    if not isinstance(accounts, dict) or set(accounts) != {x.label for x in spec.targets}:
        raise LensError("captured account labels must match the spec")
    rows: list[dict[str, Any]] = []
    for target in spec.targets:
        account = accounts[target.label]
        if not isinstance(account, dict) or set(account) != {"address", "balance", "nonce", "code", "storage"}:
            raise LensError(f"invalid account capture for {target.label}")
        if account["address"].lower() != target.address:
            raise LensError(f"address mismatch for {target.label}")
        code = account["code"]
        if not isinstance(code, str) or not HEX.fullmatch(code) or len(code) % 2:
            raise LensError(f"invalid bytecode for {target.label}")
        storage = account["storage"]
        if not isinstance(storage, dict) or set(storage) != set(target.storage_slots):
            raise LensError(f"storage evidence mismatch for {target.label}")
        normalized_storage: dict[str, str] = {}
        for slot in target.storage_slots:
            value = storage[slot]
            if not isinstance(value, str) or not HASH32.fullmatch(value):
                raise LensError(f"invalid storage value for {target.label}")
            normalized_storage[slot] = value.lower()
        rows.append({
            "block_number": number,
            "block_hash": block_hash.lower(),
            "timestamp": timestamp,
            "transaction_count": len(txs),
            "gas_used": gas_used,
            "gas_limit": gas_limit,
            "gas_utilization": round(gas_used / gas_limit, 12),
            "base_fee_wei": base_fee,
            "target": target.label,
            "address": target.address,
            "balance_wei": quantity(account["balance"], f"{target.label}.balance"),
            "nonce": quantity(account["nonce"], f"{target.label}.nonce"),
            "code_bytes": (len(code) - 2) // 2,
            "code_sha256": hashlib.sha256(bytes.fromhex(code[2:])).hexdigest(),
            "storage": normalized_storage,
        })
    return rows
