# SPDX-License-Identifier: AGPL-3.0-or-later
# Cairn — token-efficient multi-agent coordination.  © 2026 Tağmaç Çankaya
"""Cairn: coordinate multiple AI agents through a passive shared blackboard + minimal
per-agent context instead of conversation — bounded, auditable, self-terminating.

Quick start (framework-agnostic — plug your own LLM call into agent_fn):

    from cairn import run_swarm, Worker, Trace

    def agent_fn(ctx):
        # ctx.task = this agent's scope; ctx.board = compact digest of others' traces.
        # Build your prompt from ctx (minimal!), call your model, return a Trace —
        # or return None to go idle when you have nothing new (self-terminate).
        ...
        return Trace(agent=ctx.agent, kind="finding", text="...", value=2.0, anchored=False)

    result = run_swarm(agent_fn, [Worker("a", "angle A"), Worker("b", "angle B")])
    print(result.closed_reason, result.total_value())
"""
from .blackboard import Blackboard, Trace
from .valve import ValveState, TurnObs, compute_R
from .core import Worker, WorkerContext, Gardener, SwarmResult, run_swarm, AgentFn
# Optional web3 agent-economy layer (additive; stdlib-only interfaces — no web3 dependency).
# The concrete Celo adapter (cairn.web3.celo) lazy-imports web3.py; import it explicitly.
from .web3 import Receipt, IdentityAdapter, ReceiptAdapter, PaymentAdapter, NullAdapter

__version__ = "0.2.0"   # 0.2 line: web3 agent-economy layer (experimental, additive)
__all__ = [
    "Blackboard", "Trace", "ValveState", "TurnObs", "compute_R",
    "Worker", "WorkerContext", "Gardener", "SwarmResult", "run_swarm", "AgentFn",
    "Receipt", "IdentityAdapter", "ReceiptAdapter", "PaymentAdapter", "NullAdapter",
]
