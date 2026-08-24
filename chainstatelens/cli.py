"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import LensError, canonical_hash, parse_spec, project
from .rpc import JsonRpc, RpcError, collect


def load(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(value: object, path: str | None) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path:
        Path(path).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="chainstatelens", description="Read-only, block-pinned EVM state capture")
    sub = result.add_subparsers(dest="command", required=True)
    replay = sub.add_parser("replay", help="validate captured evidence and reproduce a report")
    replay.add_argument("spec")
    replay.add_argument("evidence")
    replay.add_argument("--output")
    capture = sub.add_parser("capture", help="collect allow-listed reads from an explicit RPC URL")
    capture.add_argument("spec")
    capture.add_argument("--rpc-url", required=True)
    capture.add_argument("--evidence", required=True)
    capture.add_argument("--report")
    verify = sub.add_parser("verify", help="recompute and compare a saved report")
    verify.add_argument("spec")
    verify.add_argument("evidence")
    verify.add_argument("report")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        spec = parse_spec(load(args.spec))
        if args.command == "replay":
            dump(project(spec, load(args.evidence)), args.output)
        elif args.command == "capture":
            evidence = collect(spec, JsonRpc(args.rpc_url))
            dump(evidence, args.evidence)
            dump(project(spec, evidence), args.report)
        else:
            expected = load(args.report)
            actual = project(spec, load(args.evidence))
            if canonical_hash(expected) != canonical_hash(actual):
                raise LensError("saved report does not match deterministic replay")
            print(f"verified report_sha256={actual['report_sha256']}")
    except (OSError, json.JSONDecodeError, LensError, RpcError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
