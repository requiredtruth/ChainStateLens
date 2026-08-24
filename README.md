# ChainStateLens

ChainStateLens answers a narrow reproducibility question: **what public account and storage state did an EVM JSON-RPC node return at these exact blocks, and can someone replay the evidence offline?**

```sh
./doit.sh
```

That zero-dependency command runs the test suite, compiles every module, and replays bundled synthetic evidence. No RPC endpoint, wallet, key, token, or package download is needed.

## Why this exists

Explorers show individual values and general-purpose web3 libraries expose broad APIs. ChainStateLens instead produces a small, auditable feature matrix across explicit blocks. It records block headers, balances, nonces, bytecode, and named storage slots; rechecks each block hash after collection; and makes the captured inputs sufficient for deterministic offline recomputation.

This differs from a wallet exposure diff: it is a multi-block contract/account state lens with raw evidence and reorg detection, not a portfolio interpretation. It is also not an archive node or indexer.

## Offline demonstration

```sh
./run.sh
```

## Capture public state

Create a spec with increasing block numbers and explicit public addresses/storage slots, then run:

```sh
python -m chainstatelens capture spec.json --rpc-url http://127.0.0.1:8545 \
  --evidence evidence.json --report report.json
python -m chainstatelens verify spec.json evidence.json report.json
```

The collector sends only `eth_chainId`, `eth_getBlockByNumber`, `eth_getBalance`, `eth_getTransactionCount`, `eth_getCode`, and `eth_getStorageAt`. State reads use explicit numeric block tags. The endpoint is supplied at runtime and is never saved in the report.

## Output contract

`chainstatelens/report-1` rows include the block number/hash/time, transaction count, gas use and utilization, base fee, target label/address, balance, nonce, bytecode length/hash, and requested storage values. `report_sha256` commits to the canonical report.

Errors are intentionally direct and searchable:

```text
error: block 100 changed during capture
error: saved report does not match deterministic replay
error: RPC method is not read-only allow-listed: eth_sendRawTransaction
```

## Safety and limitations

- Read-only and non-custodial: there is no signing, transaction, swap, order, approval, or key interface.
- An RPC node can lie. Evidence proves what that endpoint returned, not canonical chain truth. Compare independent trusted nodes when stakes require it.
- Historical reads require an archive-capable endpoint for old state.
- Rechecking a block hash detects a change during capture; it does not establish finality.
- Storage slots require protocol knowledge. This release does not decode ABIs, mappings, proxies, or semantic meaning.
- Addresses and storage values are public chain data but can still be sensitive in context; choose targets deliberately.
- This is measurement software, not financial, legal, security, or trading advice.

## Development support

Donations can fund more production and may request priority for a compatible direction through the issue template with a public transaction hash. They do not guarantee implementation or buy support, ownership, returns, or preference. See [SUPPORT.md](SUPPORT.md) and confirm the asset and network before sending.

Apache-2.0 licensed. See [PROJECT_SPEC.md](PROJECT_SPEC.md) for the invariant contract.
