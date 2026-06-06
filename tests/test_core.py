# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for run_swarm coordination + the optional verifiable-receipt hook."""
from cairn import run_swarm, Worker, Trace, NullAdapter, ReceiptAdapter, Receipt, Blackboard
from cairn.core import _state_hash, _run_id


def one_shot_agent():
    """Emits one finding per agent, then idles (self-terminates)."""
    seen = set()
    def fn(ctx):
        if ctx.agent in seen:
            return None
        seen.add(ctx.agent)
        return Trace(agent=ctx.agent, kind="finding", text="w", value=1.0)
    return fn


def test_workers_self_terminate():
    r = run_swarm(one_shot_agent(), [Worker("a", "A"), Worker("b", "B")])
    assert r.total_value() == 2.0
    assert "idle" in r.closed_reason


def test_max_rounds_reached():
    # never idles, always RISING (value>eps) -> hits the round cap
    r = run_swarm(lambda ctx: Trace(agent=ctx.agent, kind="finding", text="x", value=1.0),
                  [Worker("a", "A")], max_rounds=3)
    assert r.rounds == 3
    assert r.closed_reason == "max-rounds reached"


def test_trace_agent_backfilled():
    def fn(ctx):
        if ctx.round > 1:
            return None
        return Trace(agent="", kind="finding", text="x", value=1.0)   # empty -> backfilled to ctx.agent
    r = run_swarm(fn, [Worker("a", "A")])
    assert all(t.agent for t in r.traces)


def test_receipt_none_by_default():
    r = run_swarm(one_shot_agent(), [Worker("a", "A")])
    assert r.receipt is None


def test_receipt_nulladapter_is_noop():
    r = run_swarm(one_shot_agent(), [Worker("a", "A")], receipt=NullAdapter())
    assert r.receipt is not None and r.receipt.ok is False


class _FakeReceipt(ReceiptAdapter):
    def __init__(self):
        self.calls = []
    def record_run(self, run_id, state_hash, agent_count, meta_uri=""):
        self.calls.append((run_id, state_hash, agent_count))
        return Receipt(tx_hash="0xfake", chain_id=1, block=1)
    def verify(self, run_id):
        return any(c[0] == run_id for c in self.calls)


def test_receipt_hook_fires_exactly_once():
    fake = _FakeReceipt()
    r = run_swarm(one_shot_agent(), [Worker("a", "A"), Worker("b", "B")], receipt=fake)
    assert len(fake.calls) == 1, "receipt must be emitted once per run"
    assert r.receipt.ok and r.receipt.tx_hash == "0xfake"
    run_id, state_hash, n = fake.calls[0]
    assert len(state_hash) == 32 and n == 2
    assert fake.verify(run_id)


def test_state_hash_deterministic():
    b = Blackboard()
    b.append(Trace(agent="a", text="x", value=1.0))
    assert _state_hash(b) == _state_hash(b)
    assert len(_state_hash(b)) == 32


def test_run_id_explicit_passthrough():
    b = Blackboard()
    assert _run_id(b"fixed-id", b) == b"fixed-id"
