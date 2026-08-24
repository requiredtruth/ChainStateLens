"""Minimal allow-listed JSON-RPC collector."""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Callable

from .core import Spec

ALLOWED_METHODS = frozenset({"eth_chainId", "eth_getBlockByNumber", "eth_getBalance", "eth_getTransactionCount", "eth_getCode", "eth_getStorageAt"})


class RpcError(RuntimeError):
    pass


class JsonRpc:
    def __init__(self, url: str, opener: Callable[..., Any] = urllib.request.urlopen) -> None:
        if not url.startswith(("http://", "https://")):
            raise RpcError("RPC URL must use http or https")
        self.url = url
        self.opener = opener
        self.request_id = 0

    def call(self, method: str, params: list[Any]) -> Any:
        if method not in ALLOWED_METHODS:
            raise RpcError(f"RPC method is not read-only allow-listed: {method}")
        self.request_id += 1
        body = json.dumps({"jsonrpc": "2.0", "id": self.request_id, "method": method, "params": params}).encode()
        request = urllib.request.Request(self.url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with self.opener(request, timeout=30) as response:
                result = json.loads(response.read())
        except Exception as exc:
            raise RpcError(f"RPC request failed: {exc}") from exc
        if not isinstance(result, dict) or result.get("id") != self.request_id or result.get("jsonrpc") != "2.0":
            raise RpcError("malformed or mismatched RPC response")
        if "error" in result:
            raise RpcError(f"RPC error: {result['error']}")
        if "result" not in result or result["result"] is None:
            raise RpcError("RPC returned no result")
        return result["result"]


def collect(spec: Spec, rpc: JsonRpc) -> dict[str, Any]:
    chain_id = rpc.call("eth_chainId", [])
    captures: list[dict[str, Any]] = []
    for block_number in spec.blocks:
        block_tag = hex(block_number)
        block = rpc.call("eth_getBlockByNumber", [block_tag, False])
        accounts: dict[str, Any] = {}
        for target in spec.targets:
            accounts[target.label] = {
                "address": target.address,
                "balance": rpc.call("eth_getBalance", [target.address, block_tag]),
                "nonce": rpc.call("eth_getTransactionCount", [target.address, block_tag]),
                "code": rpc.call("eth_getCode", [target.address, block_tag]),
                "storage": {slot: rpc.call("eth_getStorageAt", [target.address, slot, block_tag]) for slot in target.storage_slots},
            }
        confirmed = rpc.call("eth_getBlockByNumber", [block_tag, False])
        captures.append({"block": block, "confirm_hash": confirmed.get("hash"), "accounts": accounts})
    return {"chain_id": chain_id, "captures": captures}
