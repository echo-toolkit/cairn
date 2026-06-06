# SPDX-License-Identifier: AGPL-3.0-or-later
# Cairn — web3 agent-economy layer (OPTIONAL, additive).  © 2026 Tağmaç Çankaya
"""Optional web3 layer that turns Cairn's coordination into *verifiable* coordination.

This is additive — the core library (blackboard + minimal context + valve) is unchanged
and has NO web3 dependency. The chain layer switches on only when you inject an adapter.

Three capabilities (ship in this order; each is independent):
  1. RECEIPTS  — emit a verifiable on-chain record per coordination run (run_id + state hash).
  2. IDENTITY  — give each agent a verifiable on-chain identity (ERC-8004 registries).
  3. PAYMENT   — optional agent-to-agent value rails (deferred; not needed first).

Default = NullAdapter (no-op) → `import cairn` stays dependency-free and behavior is identical.
The concrete Celo/EVM implementation lives in `cairn.web3.celo` (lazy-imports web3.py; import it
explicitly only when you need a chain). See `Dev/Cairn/web3-agent-economy.md` for the design + the
verified ERC-8004 addresses + the build/dev loop.
"""
from .adapters import (
    Receipt, IdentityAdapter, ReceiptAdapter, PaymentAdapter, NullAdapter,
)

__all__ = [
    "Receipt", "IdentityAdapter", "ReceiptAdapter", "PaymentAdapter", "NullAdapter",
]
