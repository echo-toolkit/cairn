# SPDX-License-Identifier: AGPL-3.0-or-later
# Cairn — coordination core: minimal-context workers + gardener.  © 2026 Tağmaç Çankaya
"""Framework-agnostic. Cairn does NOT call any LLM — you supply `agent_fn(ctx) -> Trace`
and make your own model/framework call inside it (OpenAI, Anthropic, LangGraph, CrewAI,
a plain script). Cairn structures HOW your agents coordinate so the bill stays bounded:

  1. minimal-context  — each agent_fn call receives only a small task scope + a bounded
     blackboard digest, never the accumulated transcript (the measured 54% lever);
  2. stigmergic blackboard — agents read/leave short traces, no conversation channel;
  3. gardener — times the close (resonance valve): stop when value has converged
     (swell) or dried up (plateau), instead of looping.

This is the preventive architecture: the structure that generates run-away spend is
removed, not capped after the fact.
"""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import Callable, Optional, TYPE_CHECKING

from .blackboard import Blackboard, Trace
from .valve import ValveState, TurnObs

if TYPE_CHECKING:
    from .web3.adapters import ReceiptAdapter


@dataclass
class Worker:
    """An agent slot: a name + its task scope (the minimal context it owns)."""
    name: str
    task: str


@dataclass
class WorkerContext:
    """Everything an agent_fn sees — deliberately minimal (task + bounded board digest)."""
    agent: str
    task: str
    board: str          # compact digest of others' traces (NOT the full history)
    round: int


# Your agent: receives a minimal context, returns a Trace, or None to go idle (self-terminate).
AgentFn = Callable[[WorkerContext], Optional[Trace]]


class Gardener:
    """Reads each round's traces and times the close via the resonance valve.
    Produces NO content — it only decides when coordination has finished."""

    def __init__(self, **valve_kwargs):
        self.valve = ValveState(**valve_kwargs)
        self.last_decision: Optional[str] = None

    def observe(self, round_traces: list[Trace], active_workers: int, label: str) -> str:
        anchored = sum(1 for t in round_traces if t.anchored)
        value = sum(t.value for t in round_traces)
        obs = TurnObs(label=label, active_workers=max(active_workers, 1),
                      anchored_workers=anchored, new_unique=len(round_traces), value=value)
        self.last_decision = self.valve.feed(obs)
        return self.last_decision

    @property
    def closed(self) -> bool:
        return self.valve.closed

    @property
    def reason(self) -> Optional[str]:
        return self.valve.closed_reason


@dataclass
class SwarmResult:
    board: Blackboard
    rounds: int
    closed_reason: str
    gardener: Gardener
    receipt: Optional[object] = None   # web3.Receipt if a ReceiptAdapter was used, else None

    @property
    def traces(self) -> list[Trace]:
        return self.board.traces

    def total_value(self) -> float:
        return self.board.total_value()


def _state_hash(board: Blackboard) -> bytes:
    """Deterministic digest of the final blackboard — the run's verifiable state fingerprint."""
    h = hashlib.sha256()
    for t in board.traces:
        h.update(t.line().encode("utf-8"))
    return h.digest()


def _run_id(explicit: Optional[bytes], board: Blackboard) -> bytes:
    if explicit is not None:
        return explicit if isinstance(explicit, (bytes, bytearray)) else str(explicit).encode()
    seed = f"{len(board)}:{board.traces[0].ts if board.traces else 0}"
    return hashlib.sha256(seed.encode()).digest()


def run_swarm(
    agent_fn: AgentFn,
    workers: list[Worker],
    *,
    max_rounds: int = 6,
    board: Optional[Blackboard] = None,
    gardener: Optional[Gardener] = None,
    digest_chars: int = 1200,
    digest_recent: int = 20,
    receipt: "Optional[ReceiptAdapter]" = None,
    run_id: Optional[bytes] = None,
) -> SwarmResult:
    """Run a bounded, blackboard-coordinated swarm.

    Each round, every still-active worker is called once with a MINIMAL context
    (its task + the bounded blackboard digest). A worker that returns None goes
    idle (self-terminated). The gardener closes the run on swell/plateau. If every
    worker idles, the run ends (workers self-terminate — efficiency by construction).

    Optional web3 layer (additive, default off): pass `receipt=` a ReceiptAdapter
    (e.g. cairn.web3.celo.CeloEVMAdapter) to emit ONE verifiable on-chain record when
    the run closes — turning coordination into *verifiable* coordination. With
    `receipt=None` there is zero chain touch and behavior is identical. See cairn.web3.
    """
    board = board or Blackboard()
    gardener = gardener or Gardener()
    active = {w.name: w for w in workers}

    reason = "max-rounds reached"
    rounds_run = max_rounds
    for rnd in range(1, max_rounds + 1):
        round_traces: list[Trace] = []
        for name, w in list(active.items()):
            ctx = WorkerContext(agent=name, task=w.task,
                                 board=board.digest(max_chars=digest_chars, recent=digest_recent),
                                 round=rnd)
            trace = agent_fn(ctx)
            if trace is None:
                del active[name]                 # worker self-terminated → idle
                continue
            if not trace.agent:
                trace.agent = name
            board.append(trace)
            round_traces.append(trace)

        gardener.observe(round_traces, active_workers=len(workers), label=f"R{rnd}")
        if gardener.closed:
            reason, rounds_run = gardener.reason or "closed", rnd
            break
        if not active:
            reason, rounds_run = "all-idle (workers self-terminated)", rnd
            break

    result = SwarmResult(board, rounds_run, reason, gardener)
    if receipt is not None:                      # optional: emit one verifiable receipt on close
        result.receipt = receipt.record_run(
            run_id=_run_id(run_id, board),
            state_hash=_state_hash(board),
            agent_count=len(workers),
        )
    return result
