# SPDX-License-Identifier: AGPL-3.0-or-later
# Cairn — web3 layer self-test (offline, no chain, no web3.py).  © 2026 Tağmaç Çankaya
"""Verifies the web3 agent-economy layer is correctly additive WITHOUT touching a chain:
  1. run_swarm with receipt=None  → behaves exactly as before (no receipt).
  2. run_swarm with NullAdapter   → safe no-op receipt (Receipt.ok is False).
  3. run_swarm with a fake on-chain adapter → emits ONE receipt on close, with run_id+state_hash.
  4. the same run produces the same state_hash (determinism) and records exactly once.

Run: python3 examples/web3_selftest.py   (no deps; does NOT import web3.py)
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from cairn import run_swarm, Worker, Trace, NullAdapter, ReceiptAdapter, Receipt


def make_agent():
    """A tiny deterministic agent: emits one finding, then idles (self-terminates)."""
    seen = set()
    def agent_fn(ctx):
        if ctx.agent in seen:
            return None
        seen.add(ctx.agent)
        return Trace(agent=ctx.agent, kind="finding", text=f"{ctx.agent} did work", value=1.0)
    return agent_fn


class FakeChainReceipt(ReceiptAdapter):
    """Pretends to be a chain: records calls in memory, returns an 'ok' Receipt."""
    def __init__(self):
        self.calls = []
    def record_run(self, run_id, state_hash, agent_count, meta_uri=""):
        self.calls.append((run_id, state_hash, agent_count, meta_uri))
        return Receipt(tx_hash="0xfake", chain_id=11142220, block=1)
    def verify(self, run_id):
        return any(c[0] == run_id for c in self.calls)


def main():
    workers = [Worker("a", "angle A"), Worker("b", "angle B")]

    # 1. no receipt → unchanged
    r0 = run_swarm(make_agent(), workers)
    assert r0.receipt is None, "receipt=None must leave receipt unset"
    assert r0.total_value() == 2.0, "core behavior changed!"

    # 2. NullAdapter → safe no-op
    r1 = run_swarm(make_agent(), workers, receipt=NullAdapter())
    assert r1.receipt is not None and r1.receipt.ok is False, "NullAdapter receipt must be no-op"

    # 3. fake chain → exactly one receipt, carrying run_id + 32-byte state_hash
    fake = FakeChainReceipt()
    r2 = run_swarm(make_agent(), workers, receipt=fake)
    assert r2.receipt.ok and r2.receipt.tx_hash == "0xfake", "fake receipt should be ok"
    assert len(fake.calls) == 1, f"must record exactly once, got {len(fake.calls)}"
    run_id, state_hash, n, _ = fake.calls[0]
    assert len(state_hash) == 32 and n == 2, "state_hash must be 32 bytes; agent_count=2"
    assert fake.verify(run_id), "verify() must find the recorded run"

    # 4. determinism — same traces → same state_hash
    from cairn.core import _state_hash
    assert _state_hash(r2.board) == state_hash, "state_hash must be deterministic"

    print("OK  web3 layer is additive: core unchanged, receipt hook fires once, hashes deterministic.")
    print(f"    null.ok={r1.receipt.ok}  fake.ok={r2.receipt.ok}  state_hash={state_hash.hex()[:16]}…")


if __name__ == "__main__":
    main()
