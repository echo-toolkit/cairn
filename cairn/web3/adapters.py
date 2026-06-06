# SPDX-License-Identifier: AGPL-3.0-or-later
# Cairn — chain-agnostic web3 adapter interfaces.  © 2026 Tağmaç Çankaya
"""Abstract adapter interfaces so Cairn's core stays chain-free (stdlib only here).

The core calls these interfaces, never a chain directly. A concrete adapter (e.g.
`cairn.web3.celo.CeloEVMAdapter`) implements them for one chain. `NullAdapter` is the
default no-op: with it, the off-chain library behaves exactly as before — the web3 layer
is purely additive and off by default.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class Receipt:
    """The verifiable artifact a chain write returns. `ok` = it actually landed on-chain."""
    tx_hash: Optional[str] = None
    chain_id: Optional[int] = None
    block: Optional[int] = None

    @property
    def ok(self) -> bool:
        return self.tx_hash is not None


class IdentityAdapter(ABC):
    """Verifiable agent identity (ERC-8004 Identity Registry on EVM chains)."""
    @abstractmethod
    def register_agent(self, registration_uri: str) -> str:
        """Register an agent (URI → hosted registration JSON). Returns the agent_id."""
    @abstractmethod
    def resolve(self, agent_id: str) -> dict:
        """Return the agent's registration JSON (or {} if unknown)."""
    @abstractmethod
    def agent_address(self, agent_id: str) -> Optional[str]:
        """Return the on-chain address that owns the agent identity, if any."""


class ReceiptAdapter(ABC):
    """Verifiable on-chain receipts of coordination runs (the grant's 'verifiable usage')."""
    @abstractmethod
    def record_run(self, run_id: bytes, state_hash: bytes,
                   agent_count: int, meta_uri: str = "") -> Receipt:
        """Emit one verifiable record for a finished coordination run."""
    @abstractmethod
    def verify(self, run_id: bytes) -> bool:
        """Was a run with this id recorded on-chain?"""


class PaymentAdapter(ABC):
    """Optional agent-to-agent value rails (deferred — not needed for receipts/identity)."""
    @abstractmethod
    def pay(self, to_agent: str, amount: int, token: Optional[str] = None) -> Receipt:
        ...
    @abstractmethod
    def balance(self, agent_or_addr: str, token: Optional[str] = None) -> int:
        ...


class NullAdapter(IdentityAdapter, ReceiptAdapter, PaymentAdapter):
    """No-op default. With this adapter the web3 layer does nothing — the core library
    runs fully off-chain and unchanged. Used so `receipt=None` and `receipt=NullAdapter()`
    are both safe, and so tests/CI never touch a chain."""
    def register_agent(self, registration_uri: str) -> str:
        return "null:0"
    def resolve(self, agent_id: str) -> dict:
        return {}
    def agent_address(self, agent_id: str) -> Optional[str]:
        return None
    def record_run(self, run_id: bytes, state_hash: bytes,
                   agent_count: int, meta_uri: str = "") -> Receipt:
        return Receipt()
    def verify(self, run_id: bytes) -> bool:
        return False
    def pay(self, to_agent: str, amount: int, token: Optional[str] = None) -> Receipt:
        return Receipt()
    def balance(self, agent_or_addr: str, token: Optional[str] = None) -> int:
        return 0
