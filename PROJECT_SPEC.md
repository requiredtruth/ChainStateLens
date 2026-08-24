# Project specification

ChainStateLens records a small, explicit matrix of public EVM state at user-selected historical blocks. Every account read is pinned to the numeric block tag, and each block hash is read again after the account reads. Replay validates the evidence and derives the report without a network connection.

It cannot send transactions, sign messages, manage keys, discover addresses, predict prices, or identify people. Unknown, missing, reorganized, malformed, or inconsistent state fails closed.
